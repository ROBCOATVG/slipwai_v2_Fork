"""A channel as a repository: what `channel check` catches before an entry joins it.

Every channel here is one the test builds, so what is proved is the check and nothing of any published
channel. The public one is checked by this code rather than by itself, which is the whole reason the check
lives in the keel.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import channel, channel_new, package_new, package_release

CORE = "9.0"


class ChannelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.channel = self.area / "channel"
        channel_new.write("a channel", self.channel)

    def register(self, key: str = "lens", version: str = "0.1.0", publisher: str = "ACME") -> Path:
        root = self.area / version / key
        package_new.write("extension", key, self.area / version, CORE)
        (root / "VERSION").write_text(f"{version}\n", encoding="utf-8")
        package_release.register(root, self.channel, publisher)
        return root

    def test_a_fresh_channel_is_missing_only_its_index_and_says_which_command_writes_it(self) -> None:
        found = channel.check(self.channel)
        self.assertEqual(len(found), 1)
        self.assertIn("channel build", found[0])

    def test_a_channel_with_one_registered_release_serves_what_it_claims_to(self) -> None:
        self.register()
        self.assertEqual(channel.check(self.channel), [])

    def test_a_release_file_changed_after_its_entry_is_caught(self) -> None:
        """The check a reviewer cannot do by reading, and the one that matters most."""
        self.register()
        archive = self.channel / "slipwai-languages/lens-0.1.0.tar.gz"
        archive.write_bytes(archive.read_bytes() + b"tampered")
        found = channel.check(self.channel)
        self.assertTrue(any("digest" in line for line in found), found)

    def test_a_release_file_that_is_not_there_at_all_is_caught(self) -> None:
        self.register()
        (self.channel / "slipwai-languages/lens-0.1.0.tar.gz").unlink()
        self.assertTrue(any("is not in this channel" in line for line in channel.check(self.channel)))

    def test_an_index_edited_by_hand_is_caught_and_the_command_that_rewrites_it_named(self) -> None:
        self.register()
        path = self.channel / "slipwai-languages/index.json"
        held = json.loads(path.read_text(encoding="utf-8"))
        held["packages"]["invented"] = []
        path.write_text(json.dumps(held), encoding="utf-8")
        found = channel.check(self.channel)
        self.assertTrue(any("channel build" in line for line in found), found)

    def test_a_second_publisher_under_a_name_the_first_holds_is_refused_by_name(self) -> None:
        """A name belongs to its first publisher: anything else has an install silently change hands."""
        self.register(version="0.1.0", publisher="ACME")
        self.register(version="0.2.0", publisher="SOMEONE-ELSE")
        found = channel.check(self.channel)
        self.assertTrue(any("ACME and SOMEONE-ELSE" in line for line in found), found)

    def test_one_publisher_releasing_twice_is_not_a_collision(self) -> None:
        self.register(version="0.1.0")
        self.register(version="0.2.0")
        self.assertEqual(channel.check(self.channel), [])

    def test_an_entry_the_client_would_drop_is_caught_rather_than_served_in_silence(self) -> None:
        """A contributor who followed the instructions and got silence is the failure this prevents."""
        self.register()
        path = self.channel / "entries/lens-0.1.0.json"
        held = json.loads(path.read_text(encoding="utf-8"))
        held["version"] = "not a version"
        path.write_text(json.dumps(held), encoding="utf-8")
        found = channel.check(self.channel)
        self.assertTrue(any("would drop this entry" in line for line in found), found)

    def test_an_entry_that_is_not_json_is_one_finding_and_never_a_traceback(self) -> None:
        self.register()
        (self.channel / "entries/broken.json").write_text("{not json", encoding="utf-8")
        found = channel.check(self.channel)
        self.assertEqual(len(found), 1)
        self.assertIn("broken.json", found[0])


class NewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def test_the_contributor_page_names_the_four_commands_and_the_two_rules(self) -> None:
        channel_new.write("a channel", self.area / "channel")
        said = (self.area / "channel/CONTRIBUTING.md").read_text(encoding="utf-8")
        for command in ("package new", "package check", "package register", "channel check"):
            self.assertIn(command, said)
        self.assertIn("belongs to its first publisher", said)
        self.assertIn("immutable", said)

    def test_its_ci_runs_the_keel_s_check_and_not_one_of_its_own(self) -> None:
        """A channel checked by itself is a channel whose check is only as good as that channel."""
        channel_new.write("a channel", self.area / "channel")
        workflow = (self.area / "channel/.github/workflows/channel.yml").read_text(encoding="utf-8")
        self.assertIn("slipwai channel check .", workflow)
        self.assertIn("pip install", workflow)

    def test_a_directory_that_already_holds_something_is_refused(self) -> None:
        from slipwai.errors import GenerationError
        channel_new.write("a channel", self.area / "channel")
        with self.assertRaises(GenerationError):
            channel_new.write("a channel", self.area / "channel")


if __name__ == "__main__":
    unittest.main()


class FreshCloneTest(unittest.TestCase):
    """`channel new` into a clone of the repository somebody just made for it, which is the normal way.

    It refused that, because `.git` counted as "already holds something" — so the instruction was to run
    it somewhere else and then turn that into a repository by hand.
    """

    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def test_a_fresh_clone_counts_as_empty(self) -> None:
        place = self.area / "channel"
        (place / ".git").mkdir(parents=True)
        (place / ".git/config").write_text("", encoding="utf-8")
        channel_new.write("a channel", place)
        self.assertTrue((place / "CONTRIBUTING.md").is_file())

    def test_and_so_do_the_files_a_new_repository_is_made_with(self) -> None:
        place = self.area / "channel"
        place.mkdir()
        for name in ("README.md", "LICENSE", ".gitignore"):
            (place / name).write_text("", encoding="utf-8")
        channel_new.write("a channel", place)
        self.assertTrue((place / "CONTRIBUTING.md").is_file())

    def test_anything_else_is_refused_and_named(self) -> None:
        """Named rather than counted, so the refusal says what to move."""
        from slipwai.errors import GenerationError
        place = self.area / "channel"
        place.mkdir()
        (place / "my-notes.md").write_text("", encoding="utf-8")
        with self.assertRaises(GenerationError) as refused:
            channel_new.write("a channel", place)
        self.assertIn("my-notes.md", str(refused.exception))


class KeelTest(unittest.TestCase):
    """Which keel checks a channel. A channel created today installed `slipwai` from PyPI, got version 1,
    and failed on its first push with `invalid choice: 'channel'` — because the verb that checks it is in
    version 2 and version 2 is not published yet. Found on the first real push of `slipwai-index`."""

    def workflow(self) -> str:
        area = Path(tempfile.mkdtemp())
        channel_new.write("a channel", area / "channel")
        return (area / "channel/.github/workflows/channel.yml").read_text(encoding="utf-8")

    def test_the_keel_can_be_named_by_a_repository_variable(self) -> None:
        self.assertIn("vars.SLIPWAI_KEEL", self.workflow())

    def test_and_defaults_to_the_published_one(self) -> None:
        """Which is what every channel should end up doing, once there is one to install."""
        self.assertIn("|| 'slipwai'", self.workflow())

    def test_it_says_which_keel_it_installed(self) -> None:
        """A check that failed against the wrong keel should not need the log read twice to see that."""
        self.assertIn("slipwai --version", self.workflow())

    def test_the_readme_says_how_to_point_it_somewhere_else(self) -> None:
        area = Path(tempfile.mkdtemp())
        channel_new.write("a channel", area / "channel")
        said = (area / "channel/README.md").read_text(encoding="utf-8")
        self.assertIn("SLIPWAI_KEEL", said)
        self.assertIn("gh variable set", said)


class HostedElsewhereTest(unittest.TestCase):
    """A release file lives on the tag that built it; the channel holds the entry.

    Git keeps every version of every file for ever, so a channel that stored its own tarballs would grow a
    copy of every release anybody ever made — and a contribution would carry a binary a reviewer cannot
    read. The six that opened this channel went from 1.2 MB to 16 KB.
    """

    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.channel = self.area / "channel"
        channel_new.write("a channel", self.channel)
        package_new.write("extension", "lens", self.area, CORE)
        (self.area / "lens/VERSION").write_text("1.0.0\n", encoding="utf-8")
        self.url = "https://example.invalid/lens/releases/download/v1.0.0/lens-1.0.0.tar.gz"

    def test_the_entry_names_the_url_and_the_channel_holds_no_tarball(self) -> None:
        archive, entry_file, _ = package_release.register(
            self.area / "lens", self.channel, "ACME", file_url=self.url)
        self.assertIsNone(archive)
        self.assertEqual(json.loads(entry_file.read_text(encoding="utf-8"))["file"], self.url)
        self.assertEqual(list((self.channel / "slipwai-languages").glob("*.tar.gz")), [])

    def test_the_digest_is_still_of_the_bytes_that_were_built(self) -> None:
        """Which is the whole of what makes somebody else's URL safe to list."""
        _, entry_file, _ = package_release.register(
            self.area / "lens", self.channel, "ACME", file_url=self.url)
        held = json.loads(entry_file.read_text(encoding="utf-8"))
        self.assertRegex(held["sha256"], r"^[0-9a-f]{64}$")

    def test_a_check_that_does_not_fetch_passes_without_reaching_the_network(self) -> None:
        """A person checking a channel on a train should not wait on a hundred downloads."""
        package_release.register(self.area / "lens", self.channel, "ACME", file_url=self.url)
        self.assertEqual(channel.check(self.channel), [])

    def test_a_file_hosted_elsewhere_is_recognised_as_such(self) -> None:
        self.assertEqual(channel.elsewhere({"file": self.url}), self.url)
        self.assertEqual(channel.elsewhere({"file": "lens-1.0.0.tar.gz"}), "")

    def test_a_local_file_that_is_not_there_says_the_entry_names_no_url_either(self) -> None:
        """The two ways an entry can name bytes, and a refusal that mentions only one would read as
        though the other were not allowed."""
        package_release.register(self.area / "lens", self.channel, "ACME")
        for path in (self.channel / "slipwai-languages").glob("*.tar.gz"):
            path.unlink()
        found = channel.check(self.channel)
        self.assertTrue(any("names no URL it is at instead" in line for line in found), found)

    def test_a_url_that_cannot_be_fetched_is_a_finding_when_fetching(self) -> None:
        """A file the index names and nobody can reach is an entry that installs for nobody."""
        package_release.register(self.area / "lens", self.channel,
                                 "ACME", file_url=(self.area / "nothing.tar.gz").as_uri())
        found = channel.check(self.channel, fetch_remote=True)
        self.assertTrue(any("could not be fetched" in line for line in found), found)

    def test_a_url_whose_bytes_are_not_the_digest_is_caught_when_fetching(self) -> None:
        """The publisher can replace the asset and nobody can stop them. This is what it costs them."""
        other = self.area / "something-else.tar.gz"
        other.write_bytes(b"not the package")
        package_release.register(self.area / "lens", self.channel, "ACME", file_url=other.as_uri())
        found = channel.check(self.channel, fetch_remote=True)
        self.assertTrue(any("not the file the entry publishes a digest of" in line for line in found), found)

    def test_the_channel_s_ci_fetches(self) -> None:
        """Which is where a pull request from somebody nobody knows is actually decided."""
        said = (self.channel / ".github/workflows/channel.yml").read_text(encoding="utf-8")
        self.assertIn("slipwai channel check . --fetch", said)
