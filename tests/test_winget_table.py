import unittest
from modules.software_updates import parse_upgrade_table


class WingetTableTests(unittest.TestCase):
    def test_parses_table(self):
        lines = ['Name             Id                 Version     Available     Source',
                 '--------------------------------------------------------------------',
                 'Sample Editor    Vendor.Editor      1.2.0       1.3.0         winget',
                 'Sample Tool      Vendor.Tool        4.0         4.1           winget',
                 '2 upgrades available.']
        self.assertEqual(parse_upgrade_table(lines), [
            ('Sample Editor', 'Vendor.Editor', '1.2.0', '1.3.0'),
            ('Sample Tool', 'Vendor.Tool', '4.0', '4.1')])

    def test_unknown_language_returns_none(self):
        self.assertIsNone(parse_upgrade_table(['Name  Kennung  Version  Verfuegbar']))

    def test_empty_recognized_table(self):
        self.assertEqual(parse_upgrade_table(['Name    Id    Version    Available', '----------------']), [])

    def test_adjacent_columns_with_long_package_names(self):
        lines = [
            'Name                  Id                           Version          Available         Source',
            '--------------------------------------------------------------------------------------------',
            'Epic Online Services  EpicGames.EpicOnlineServices 4.2.1            4.3.1             winget',
            'Sunshine              LizardByte.Sunshine          2026.516.143833  2026.914.233613 winget',
            '2 upgrades available.',
            '1 package(s) have version numbers that cannot be determined.',
        ]
        self.assertEqual(parse_upgrade_table(lines), [
            ('Epic Online Services', 'EpicGames.EpicOnlineServices', '4.2.1', '4.3.1'),
            ('Sunshine', 'LizardByte.Sunshine', '2026.516.143833', '2026.914.233613'),
        ])
