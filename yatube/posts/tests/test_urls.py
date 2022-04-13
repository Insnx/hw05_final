from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from http import HTTPStatus
from ..models import Post, Group, User

User = get_user_model()


class TaskURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()  # дополняем функционалом из родителя
        cls.user_author = User.objects.create_user(username='author')
        cls.user_simple = User.objects.create_user(username='simple_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user_author,
            text='Тестовая пост',
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем пользователя
        # self.user = User.objects.create_user(username='HasNoName')
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user_simple)
        # Создаем третьего клиента
        self.authorized_client_author = Client()
        # Авторизуем пользователя
        self.authorized_client_author.force_login(self.user_author)

    def test_home_url_exists_at_desired_location(self):
        """Страница / доступна любому пользователю."""
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK.value)
        self.assertTemplateUsed(response, 'posts/index.html')

    def test_group_added_url_exists_at_desired_location(self):
        """Страница /group/test-slug/ доступна любому пользователю."""
        response = self.guest_client.get('/group/test-slug/')
        self.assertEqual(response.status_code, HTTPStatus.OK.value)
        self.assertTemplateUsed(response, 'posts/group_list.html')

    # Проверяем доступность страниц для авторизованного пользователя
    def test_username_list_url_exists_at_desired_location(self):
        """Страница /username/author/ доступна авторизованному пользователю."""
        response = self.authorized_client.get('/profile/simple_user/')
        self.assertEqual(response.status_code, HTTPStatus.OK.value)
        self.assertTemplateUsed(response, 'posts/profile.html')

    def test_post_detail_url_exists_at_desired_location_authororized(self):
        """Страница /post/id/ доступна авторизованному
        пользователю."""
        response = self.authorized_client.get(f'/posts/{self.post.id}/')
        self.assertEqual(response.status_code, HTTPStatus.OK.value)
        self.assertTemplateUsed(response, 'posts/post_detail.html')

    # Проверяем редиректы для неавторизованного пользователя
    def test_post_edit_url_redirect_nonauthor(self):
        """Страница /post/edit/ перенаправляет анонимного пользователя."""
        response = self.guest_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND.value)
        response = self.authorized_client_author.get(
            f'/posts/{self.post.id}/edit/')
        self.assertTemplateUsed(response, 'posts/create_post.html')
        self.assertEqual(response.status_code, HTTPStatus.OK.value)
        response = self.authorized_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND.value)

    def test_post_create_url_redirect_anonymous(self):
        """Страница /create/ перенаправляет анонимного
        пользователя.
        """
        response = self.guest_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND.value)
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK.value)
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_task_detail_url_redirect_anonymous(self):
        """Страница /unexisting_page/ выдает ошибку о несуществующей страницы
        """
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND.value)
        response = self.authorized_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND.value)
