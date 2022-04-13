# deals/tests/test_views.py
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from ..models import Post, Group, User

User = get_user_model()


class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()  # дополняем функционалом из родителя
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            group=cls.group
        )
        cls.posts = [
            Post.objects.create(
                author=cls.user,
                text='Post text № {i}',
                group=cls.group
            )
            for i in range(12)
        ]

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_contains_ten_records(self):
        reverse_dict_paginator_test = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={
                    'slug': self.group.slug}),
            reverse('posts:profile', kwargs={
                    'username': self.user.username})
        ]
        for reverse_name in reverse_dict_paginator_test:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        """Паджинатор выводит оставшиеся 3 записи на вторую страницу."""
        reverse_dict_for_paginator_test = [
            reverse('posts:index') + '?page=2',
            reverse(
                'posts:group_list', kwargs={
                    'slug': self.group.slug}) + '?page=2',
            reverse(
                'posts:profile', kwargs={
                    'username': self.user.username}) + '?page=2'
        ]
        for reverse_name in reverse_dict_for_paginator_test:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']), 3)
