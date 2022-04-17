# deals/tests/tests_form.py
import shutil
import tempfile

from django.contrib.auth import get_user_model
from ..forms import PostForm
from ..models import Post, Group, User, Comment
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

User = get_user_model()

# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


# Для сохранения media-файлов в тестах будет использоваться
# временная папка TEMP_MEDIA_ROOT, а потом мы ее удалим
@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем запись в базе данных для проверки сушествующего slug
        cls.user = User.objects.create_user(username='author')

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug',
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text='тестовый текст',
            group=cls.group,
        )

        cls.other_post = Post.objects.create(
            author=cls.user,
            text='тестовый текст другого поста',
            group=cls.group,
        )

        cls.comment = Comment.objects.create(
            author=cls.user,
            text='тест комментарий'
        )

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

        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': self.post.text,
            'group': self.group.pk,
            'image': self.uploaded.name,
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse('posts:profile', kwargs={
            'username': self.user}))
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        last_object = Post.objects.order_by("-id").last()
        self.assertEqual(form_data['text'], last_object.text)
        self.assertEqual(form_data['group'], last_object.group.pk)
        self.assertEqual(form_data['image'], self.uploaded.name)

    def test_create_post_empty_image(self):
        """тест на пустую картинку."""
        ssmall_empty = (b'')

        empty_image = SimpleUploadedFile(
            name='small_empty.gif',
            content=ssmall_empty,
            content_type='image/gif'
        )
        form_data = {
            'text': self.post.text,
            'group': self.group.pk,
            'image': empty_image,
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertFormError(
            response,
            'form',
            'image',
            'Отправленный файл пуст.'
        )

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        form_data = {
            'text': self.post.text,
            'group': self.group.pk,
            'image': self.uploaded.name,

        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(form_data['text'], self.post.text)
        self.assertEqual(form_data['group'], self.post.group.pk)
        self.assertEqual(form_data['image'], self.uploaded.name)

    def test_create_comment(self):
        """Авторизованный пользователь создает комментарий к посту."""
        comment_count = Comment.objects.count()

        form_data = {
            'text': self.comment.text,
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        last_object = Comment.objects.order_by("-id").first()
        self.assertEqual(form_data['text'], last_object.text)
