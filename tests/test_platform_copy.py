import unittest
from social_ui import platform_default_copy


class PlatformCopyTests(unittest.TestCase):
    def test_instagram_draft_uses_its_package_and_legacy_copy_remains_supported(self):
        legacy=dict(title='Existing manual title',description='Existing manual description')
        self.assertEqual(platform_default_copy('instagram',legacy),legacy)
        copy=dict(legacy,platforms={'Instagram Reels':dict(caption='Specific Instagram caption',hashtags=['#London'])})
        self.assertEqual(platform_default_copy('youtube',copy),legacy)
        self.assertEqual(platform_default_copy('instagram',copy),dict(title=legacy['title'],description='Specific Instagram caption\n\n#London'))
        self.assertEqual(legacy,dict(title='Existing manual title',description='Existing manual description'))
