#!/usr/bin/env python3
import os
import sys
import unittest
from unittest.mock import patch

# Giả sử file cupp.py chứa các hàm cần thiết từ phiên bản mở rộng
from handle import (
    read_config,
    CONFIG,
    leet_convert,
    generate_basic_wordlist,
    get_parser,
    main,
    generate_secure_password,
    PCFGPasswordGenerator,
)

class TestPasswordGenerator(unittest.TestCase):
    def setUp(self):
        # Initialize with default config
        
        read_config("cupp.cfg")
        
    def test_leet_convert(self):
        self.assertEqual(leet_convert("test"), "7357")
        self.assertEqual(leet_convert("password"), "p4ssw0rd")
        
    
    def test_config_loading(self):
        self.assertTrue("years" in CONFIG)
        self.assertTrue("specialchars" in CONFIG)
        self.assertTrue("wcfrom" in CONFIG)
        self.assertTrue("wcto" in CONFIG)

    def test_argument_parser(self):
        parser = get_parser()
        # Test interactive mode
        args = parser.parse_args(['-i'])
        self.assertTrue(args.interactive)
        
        # Test config file
        args = parser.parse_args(['-c', 'custom.cfg'])
        self.assertEqual(args.config, 'custom.cfg')

    @patch('builtins.input', side_effect=['John', 'Doe', '01011990', '', '', 'Company'])
    def test_interactive_mode(self, mock_input):
        parser = get_parser()
        args = parser.parse_args(['-i'])
        # Add your interactive mode test here if needed

    def test_generate_basic_wordlist(self):
        profile = {
            "first_name": "Dang",
            "surname": "Long",
            "birthdate": "27102000"
        }
        wordlist = generate_basic_wordlist(profile)
        
        # Check if variations of the first name are in the wordlist
        self.assertIn("long", wordlist)
        self.assertIn("Long", wordlist)
        self.assertIn("gnoL", wordlist)  # reversed
        
        # Check if birthdate variations are in the wordlist
        self.assertIn("27102000", wordlist)
        self.assertIn("2000", wordlist)
        self.assertIn("2710", wordlist)

    def test_generate_basic_wordlist_includes_short_names(self):
        profile = {
            "first_name": "Anh",
            "surname": "Tran",
            "relative_name": "Lan",
            "child_name": "Binh",
            "birthdate": "01012000"
        }
        wordlist = generate_basic_wordlist(profile, 6, 10)

        # Short names should still appear even if they are below wcfrom
        self.assertIn("lan", wordlist)
        self.assertIn("Lan", wordlist)
        self.assertIn("binh", wordlist)
        self.assertIn("Binh", wordlist)
        self.assertIn("anhtran", wordlist)

    def test_generate_secure_password(self):
        # Test default password length
        password = generate_secure_password()
        self.assertEqual(len(password), 12)
        
        # Test custom password length
        password = generate_secure_password(length=16)
        self.assertEqual(len(password), 16)
        
        # Test password contains digits
        password = generate_secure_password(use_digits=True)
        self.assertTrue(any(char.isdigit() for char in password))
        
        # Test password contains special characters
        password = generate_secure_password(use_special=True)
        self.assertTrue(any(char in CONFIG["specialchars"] for char in password))
        
        # Test password contains uppercase letters
        password = generate_secure_password(use_uppercase=True)
        self.assertTrue(any(char.isupper() for char in password))

    def test_generate_basic_wordlist(self):
        profile = {
            "first_name": "Dang",
            "surname": "Long",
            "birthdate": "27102000"
        }
        wordlist = generate_basic_wordlist(profile)
        
        # Check if variations of the first name are in the wordlist
        self.assertIn("long", wordlist)
        self.assertIn("Long", wordlist)
        self.assertIn("gnoL", wordlist)  # reversed
        
        # Check if birthdate variations are in the wordlist
        self.assertIn("27102000", wordlist)
        self.assertIn("2000", wordlist)
        self.assertIn("2710", wordlist)

    def test_pcfg_password_generator(self):
        generator = PCFGPasswordGenerator()
        password = generator.generate_password()
        
        # Check if password is not empty
        self.assertTrue(password)
        
        # Check if password length is reasonable
        self.assertGreaterEqual(len(password), 6)
        self.assertLessEqual(len(password), 16)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'])  # Ignore command line arguments when running tests
