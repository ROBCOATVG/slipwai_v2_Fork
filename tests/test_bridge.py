"""The bridge: the board as a page, and the three things a person can do to a run from it.

The point of the page is not that it is prettier than the terminal. It is that a person answers from one
seat — so the test that matters most is that an answer typed on the page becomes a line in the right
stream's own log, which is the file the captain reads at its next boundary.
"""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.bridge import serve, tell
from slipwai.bridge_page import PLAIN, page, read_only
from slipwai.cli_fleet import config
from slipwai.fleet import board
from slipwai.project.harbour import START, harbour_config
from slipwai.telegraph import MEANS


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".slipwai").mkdir()
        (self.root / "harbour.json").write_text(harbour_config(), encoding="utf-8")
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))

    def deck(self, fairway: str, *entries: logs.Entry) -> None:
        path = self.root / logs.deck_path("ordering", fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())

    def read(self, fairway: str) -> list[logs.Entry]:
        path = self.root / logs.deck_path("ordering", fairway)
        return logs.fold(path.read_text(encoding="utf-8").splitlines())

    def rendered(self, controls: bool = True) -> str:
        held = config(self.root)
        return page(board(self.root, held), held, controls=controls)


class TellTest(Fixture):
    def test_an_answer_becomes_a_told_line_in_that_stream_s_own_log(self) -> None:
        """The whole point of the page: a message somewhere else is a message nothing is watching."""
        tell(self.root, "ORD", "stop and talk to me")
        told = [e for e in self.read("ORD") if e.kind == "told"]
        self.assertEqual(len(told), 1)
        self.assertEqual(told[0].fields["message"], "stop and talk to me")

    def test_a_stream_with_no_log_says_so_rather_than_making_one(self) -> None:
        with self.assertRaises(ValueError) as refused:
            tell(self.root, "NOPE", "hello")
        self.assertIn("no log here", str(refused.exception))

    def test_an_empty_message_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            tell(self.root, "ORD", "   ")


class PageTest(Fixture):
    def test_every_label_is_the_plain_word_and_never_the_method_s(self) -> None:
        """The nautical names are the method's. Somebody reading a dashboard should not need a glossary."""
        said = self.rendered()
        for name in MEANS:
            with self.subTest(number=name):
                self.assertIn(PLAIN[name], said)
                self.assertNotIn(f">{name}<", said)

    def test_it_leads_with_what_is_waiting_on_a_person(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="look at this"))
        said = self.rendered()
        self.assertLess(said.index("Waiting on you"), said.index("Streams"))
        self.assertIn("look at this", said)

    def test_a_message_from_a_person_is_escaped_and_never_rendered_as_markup(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="<script>alert(1)</script>"))
        self.assertNotIn("<script>alert(1)</script>", self.rendered())

    def test_the_dial_shows_where_it_is_and_what_else_there_is(self) -> None:
        said = self.rendered()
        self.assertIn("Half ahead", said)
        self.assertIn("Dead slow", said)

    def test_the_read_only_copy_is_the_same_page_with_nothing_to_press(self) -> None:
        said = read_only(board(self.root, config(self.root)), config(self.root))
        self.assertNotIn("<button", said)
        self.assertNotIn("<script>", said)
        self.assertIn("Streams", said)


class ServerTest(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.server = serve(self.root, "127.0.0.1", 0)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)

    def get(self, path: str) -> tuple[int, str]:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as answer:
            return answer.status, answer.read().decode("utf-8")

    def post(self, path: str, body: dict) -> tuple[int, str]:
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                         data=json.dumps(body).encode("utf-8"),
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=5) as answer:
                return answer.status, answer.read().decode("utf-8")
        except urllib.error.HTTPError as answer:
            with answer:  # closed here, or the warning filter turns a refusal into noise in every run
                return answer.code, answer.read().decode("utf-8")

    def test_it_binds_this_machine_only(self) -> None:
        """The page changes what a run does; a default that put that on a shared network would be wrong
        once and then permanently."""
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_the_page_is_served(self) -> None:
        code, said = self.get("/")
        self.assertEqual(code, 200)
        self.assertIn("Streams", said)

    def test_the_board_is_also_json_for_anything_that_would_rather_read_it(self) -> None:
        code, said = self.get("/board.json")
        self.assertEqual(code, 200)
        self.assertIn("berths", json.loads(said))

    def test_an_answer_posted_from_the_page_reaches_the_log(self) -> None:
        code, _ = self.post("/tell", {"fairway": "ORD", "message": "from the page"})
        self.assertEqual(code, 200)
        self.assertEqual([e.fields["message"] for e in self.read("ORD") if e.kind == "told"],
                         ["from the page"])

    def test_ringing_from_the_page_writes_the_same_file_the_verb_does(self) -> None:
        """A second path that wrote harbour.json its own way would be the first one to drift."""
        code, _ = self.post("/ring", {"position": "dead-slow"})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads((self.root / "harbour.json").read_text())["position"], "dead-slow")

    def test_setting_one_number_from_the_page_leaves_the_rest(self) -> None:
        self.post("/set", {"pairs": ["boilers=1"]})
        held = json.loads((self.root / "harbour.json").read_text())
        self.assertEqual(held["boilers"], 1)
        self.assertEqual(held["position"], START)

    def test_a_position_that_is_not_one_is_a_refusal_and_not_a_traceback(self) -> None:
        code, said = self.post("/ring", {"position": "flank"})
        self.assertEqual(code, 400)
        self.assertIn("full-ahead", said)

    def test_a_route_it_has_not_got_says_what_it_has(self) -> None:
        code, said = self.post("/anything", {})
        self.assertEqual(code, 404)


class ReadOnlyServerTest(Fixture):
    def test_the_published_copy_refuses_every_control(self) -> None:
        server = serve(self.root, "127.0.0.1", 0, controls=False)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        request = urllib.request.Request(f"http://127.0.0.1:{port}/tell", data=b"{}",
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(request, timeout=5).close()
            self.fail("a read-only copy accepted a control")
        except urllib.error.HTTPError as answer:
            with answer:
                self.assertEqual(answer.code, 403)


if __name__ == "__main__":
    unittest.main()
