# deals/tests/test_views.py
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from ..models import Post, Group, User, Follow
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
import tempfile
from django.core.cache import cache
import shutil


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug',
        )
        cls.user = User.objects.create_user(username='Val')
        cls.other_user = User.objects.create_user(username='Valval')

        cls.post = Post.objects.create(
            author=cls.user,
            text='Post text for TEST',
            group=cls.group,
            image=cls.uploaded
        )
        cls.other_group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-other_slug'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        cache.clear()

    def setUp(self):
        # Создаем авторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_pages_names = {
            reverse('about:author'): 'about/author.html',
            reverse('about:tech'): 'about/tech.html',
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user.username}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}):
            'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}):
            'posts/create_post.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_index(self):
        """Проверяем контекст страницы index"""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        context_objects = {
            self.user: first_object.author,
            self.post.text: first_object.text,
            self.group: first_object.group,
            self.post.id: first_object.id,
            self.post.image: first_object.image
        }
        for reverse_name, response_name in context_objects.items():
            with self.subTest(reverse_name=reverse_name):
                self.assertEqual(response_name, reverse_name)

    def test_post_group_list(self):
        """Проверяем контекст страницы group_list"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        for post in response.context['page_obj']:
            self.assertEqual(post.group, self.group)
            self.assertEqual(post.image, self.post.image)

    def test_post_profile(self):
        """Проверяем контекст страницы profile"""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        for post in response.context['page_obj']:
            self.assertEqual(post.author, self.user)
            self.assertEqual(post.image, self.post.image)

    def test_post_post_detail(self):
        """Проверяем контекст страницы post_detail"""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id})).context['post']
        self.assertEqual(response.pk, self.post.pk)
        self.assertEqual(response.image, self.post.image)

    def test_post_create_post(self):
        """Проверяем контекст страницы post_create"""
        response = self.authorized_client.get(
            reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_post(self):
        """Проверяем контекст страницы post_edit"""
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': TaskPagesTests.post.id},
            ))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_new_create(self):
        """Проверяем, что при создании поста:
        пост появляется на главной странице,
        на странице выбранной группы,
        в профайле пользователя"""
        new_post = Post.objects.create(
            author=self.user,
            text=self.post.text,
            group=self.group
        )
        exp_pages = [
            reverse('posts:index'),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.user.username})
        ]
        for rev in exp_pages:
            with self.subTest(rev=rev):
                response = self.authorized_client.get(rev)
                self.assertIn(
                    new_post, response.context['page_obj']
                )

    def test_post_new_not_in_group(self):
        """Проверяем, что созданный пост не попал в другую группу,
        для которой не был предназначен."""
        new_post = Post.objects.create(
            author=self.user,
            text=self.post.text,
            group=self.group
        )
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.other_group.slug})
        )
        self.assertNotIn(new_post, response.context['page_obj'])

    def test_cache_index(self):
        """Проверка работы кэша на главной."""
        self.post = Post.objects.create(
            author=self.user,
            text='test-post',
            group=self.group,
        )
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        before_delete = response.content
        delete_post = Post.objects.get(id=self.post.id)
        delete_post.delete()
        after_delet = response.content
        self.assertEqual(after_delet, before_delete)
        cache.delete('index_page')
        self.assertEqual(after_delet, before_delete)

    def test_follow_for_auth(self):
        """Проверяем функцию подписки"""
        follow_count = Follow.objects.count()
        Follow.objects.create(
            user=self.user,
            author=self.other_user
        )
        self.authorized_client.post(reverse(
            'posts:profile_follow', kwargs={'username': self.other_user}))
        self.assertTrue(Follow.objects.filter(
            user=self.user, author=self.other_user).exists()
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)

    def test_unfollow_for_auth(self):
        """Проверяем функцию отписки"""
        Follow.objects.create(
            user=self.user,
            author=self.other_user
        )
        follow_count = Follow.objects.count()
        self.authorized_client.post(reverse(
            'posts:profile_unfollow', kwargs={'username': self.other_user}))
        self.assertFalse(Follow.objects.filter(
            user=self.user, author=self.other_user).exists()
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)
