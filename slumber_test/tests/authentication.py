from datetime import datetime
from mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import TestCase

from slumber import client
from slumber.connector.authentication import Backend, \
    ImproperlyConfigured
from slumber.test import mock_client
from slumber_test.tests.configurations import ConfigureAuthnBackend, \
    PatchForAuthnService


class TestBackend(PatchForAuthnService, TestCase):
    def setUp(self):
        super(TestBackend, self).setUp()
        self.backend = Backend()

    def test_remote_user(self):
        user = client.auth.django.contrib.auth.User.get(username='test')
        for attr in ['is_active', 'is_staff', 'date_joined', 'is_superuser',
                'first_name', 'last_name', 'email', 'username']:
            self.assertTrue(hasattr(user, attr), user.__dict__.keys())

    def test_get_user(self):
        user = self.backend.get_user(self.user.username)
        self.assertEqual(user.username, self.user.username)
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(hasattr(user, 'remote_user'))
        self.assertEqual(user.username, user.remote_user.username)
        self.assertEqual(user.is_active, user.remote_user.is_active)
        self.assertEqual(user.is_staff, user.remote_user.is_staff)
        self.assertEqual(user.is_superuser, user.remote_user.is_superuser)

    def test_group_permissions(self):
        user = self.backend.get_user(self.user.username)
        self.assertTrue(hasattr(user, 'remote_user'))
        perms = self.backend.get_group_permissions(user)
        self.assertEqual(perms, self.user.get_group_permissions())

    def test_all_permissions(self):
        user = self.backend.get_user(self.user.username)
        self.assertTrue(hasattr(user, 'remote_user'))
        perms = self.backend.get_all_permissions(user)
        self.assertEqual(perms, self.user.get_all_permissions())

    def test_module_perms(self):
        user = self.backend.get_user(self.user.username)
        self.assertTrue(hasattr(user, 'remote_user'))
        self.assertFalse(self.backend.has_module_perms(user, 'slumber_test'))

    def test_permission(self):
        user = self.backend.get_user(self.user.username)
        self.assertTrue(hasattr(user, 'remote_user'))
        self.assertFalse(self.backend.has_perm(user, 'slumber_test.add_pizza'))


class AuthenticationTests(ConfigureAuthnBackend, TestCase):
    def save_user(self, request):
        self.user = request.user
        return HttpResponse('ok')

    @mock_client()
    def test_isnt_authenticated(self):
        with patch('slumber_test.views._ok_text', self.save_user):
            self.client.get('/')
        self.assertFalse(self.user.is_authenticated())

    @mock_client(
        django__contrib__auth__User = [],
    )
    def test_improperly_configured(self):
        with self.assertRaises(ImproperlyConfigured):
            self.client.get('/', HTTP_X_FOST_USER='testuser')

    @mock_client(
        auth__django__contrib__auth__User = [
            dict(username='testuser', is_active=True, is_staff=True,
                date_joined=datetime.now(), is_superuser=False,
                    first_name='Test', last_name='User',
                    email='test@example.com')],
    )
    def test_is_authenticated(self):
        with patch('slumber_test.views._ok_text', self.save_user):
            self.client.get('/', HTTP_X_FOST_USER='testuser')
        self.assertTrue(self.user.is_authenticated())

    @mock_client(
        auth__django__contrib__auth__User = [
            dict(username='admin', is_active=True, is_staff=True)],
    )
    def test_admin_is_authenticated(self):
        admin = User(username='admin')
        admin.save()
        with patch('slumber_test.views._ok_text', self.save_user):
            self.client.get('/', HTTP_X_FOST_USER=admin.username)
        self.assertTrue(self.user.is_authenticated())
        self.assertEqual(admin, self.user)

    @mock_client(
        auth__django__contrib__auth__User = []
    )
    def test_remote_user_not_found(self):
        with patch('slumber_test.views._ok_text', self.save_user):
            self.client.get('/', HTTP_X_FOST_USER='testuser')
        self.assertFalse(self.user.is_authenticated())

