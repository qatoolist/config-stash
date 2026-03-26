"""Tests for file change tracking."""

import os
import shutil
import tempfile
import time
import unittest

from config_stash.file_tracker import FileTracker


class TestFileTracker(unittest.TestCase):
    """Test file change tracker."""


    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("initial content")
        self.tracker = FileTracker()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_track_file(self):
        """Test tracking a file."""
        self.tracker.track_file(self.test_file)
        self.assertIn(self.test_file, self.tracker._file_hashes)
        self.assertIn(self.test_file, self.tracker._file_mtimes)

    def test_has_changed_untracked(self):
        """Test has_changed for untracked file."""
        # Untracked files should be considered changed
        self.assertTrue(self.tracker.has_changed(self.test_file))

    def test_has_changed_not_changed(self):
        """Test has_changed for unchanged file."""
        self.tracker.track_file(self.test_file)
        self.assertFalse(self.tracker.has_changed(self.test_file))

    def test_has_changed_modified(self):
        """Test has_changed for modified file."""
        self.tracker.track_file(self.test_file)
        # Modify file
        time.sleep(0.01)  # Small delay to ensure different mtime
        with open(self.test_file, "w") as f:
            f.write("modified content")
        self.assertTrue(self.tracker.has_changed(self.test_file))

    def test_has_changed_deleted(self):
        """Test has_changed for deleted file."""
        self.tracker.track_file(self.test_file)
        os.unlink(self.test_file)
        self.assertTrue(self.tracker.has_changed(self.test_file))

    def test_get_changed_files(self):
        """Test getting list of changed files."""
        file1 = os.path.join(self.temp_dir, "file1.txt")
        file2 = os.path.join(self.temp_dir, "file2.txt")
        with open(file1, "w") as f:
            f.write("content1")
        with open(file2, "w") as f:
            f.write("content2")

        self.tracker.track_file(file1)
        self.tracker.track_file(file2)

        # Modify file1
        time.sleep(0.01)
        with open(file1, "w") as f:
            f.write("modified1")

        changed = self.tracker.get_changed_files([file1, file2])
        self.assertIn(file1, changed)
        self.assertNotIn(file2, changed)

    def test_update_tracking(self):
        """Test updating tracking information."""
        self.tracker.track_file(self.test_file)
        initial_hash = self.tracker._file_hashes[self.test_file]

        # Modify file
        time.sleep(0.01)
        with open(self.test_file, "w") as f:
            f.write("new content")

        # Update tracking
        self.tracker.update_tracking(self.test_file)
        new_hash = self.tracker._file_hashes[self.test_file]

        self.assertNotEqual(initial_hash, new_hash)
        self.assertFalse(self.tracker.has_changed(self.test_file))

    def test_clear(self):
        """Test clearing tracking information."""
        self.tracker.track_file(self.test_file)
        self.assertGreater(len(self.tracker._file_hashes), 0)

        self.tracker.clear()
        self.assertEqual(len(self.tracker._file_hashes), 0)
        self.assertEqual(len(self.tracker._file_mtimes), 0)

    def test_get_file_hash(self):
        """Test getting file hash."""
        hash1 = self.tracker.get_file_hash(self.test_file)
        self.assertIsNotNone(hash1)
        self.assertIsInstance(hash1, str)

        # Same file should have same hash
        hash2 = self.tracker.get_file_hash(self.test_file)
        self.assertEqual(hash1, hash2)

    def test_get_file_hash_modified(self):
        """Test file hash changes when file is modified."""
        hash1 = self.tracker.get_file_hash(self.test_file)

        # Modify file
        with open(self.test_file, "w") as f:
            f.write("different content")

        hash2 = self.tracker.get_file_hash(self.test_file)
        self.assertNotEqual(hash1, hash2)

    def test_get_file_hash_nonexistent(self):
        """Test getting hash for non-existent file."""
        nonexistent = os.path.join(self.temp_dir, "nonexistent.txt")
        hash_val = self.tracker.get_file_hash(nonexistent)
        self.assertIsNone(hash_val)

    def test_get_file_mtime(self):
        """Test getting file modification time."""
        mtime = self.tracker.get_file_mtime(self.test_file)
        self.assertIsNotNone(mtime)
        self.assertIsInstance(mtime, float)
        self.assertGreater(mtime, 0)

    def test_get_file_mtime_nonexistent(self):
        """Test getting mtime for non-existent file."""
        nonexistent = os.path.join(self.temp_dir, "nonexistent.txt")
        mtime = self.tracker.get_file_mtime(nonexistent)
        self.assertIsNone(mtime)


if __name__ == "__main__":
    unittest.main()
