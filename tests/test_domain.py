"""`.specify/domain/`: what is true about the domain, kept apart from what this product chose.

Issue #27. In the experiment the skipper parked on questions a written fact would have answered, and guessed
at others it should have parked on — and the two look identical from outside, because neither says what it
was decided from. The missing thing was never judgement. It was a place for facts, and a rule that a
decision taken from one cites it.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.project import cruise_agents, domain


def flat(text: str) -> str:
    return " ".join(text.split())


class DomainPageTest(unittest.TestCase):
    def page(self) -> str:
        return flat(domain.domain_readme())

    def test_it_ships_one_page_and_no_facts(self) -> None:
        """A template fact is a fact nobody wrote, and a first reader could not tell which were real."""
        files = domain.domain_files()
        self.assertEqual(list(files), [f"{domain.DOMAIN}/README.md"])
        self.assertIn("ships empty on purpose", self.page())

    def test_it_separates_a_domain_fact_from_a_product_decision(self) -> None:
        """The constitution, the specification and the owner brief each already own one of those."""
        page = self.page()
        self.assertIn("as distinct from what this product has chosen", page)
        self.assertIn("What this product decided", page)

    def test_a_fact_carries_where_it_came_from(self) -> None:
        """Because the source outlasts the number, and the number is what changes."""
        page = self.page()
        self.assertIn("The source matters more than the number", page)

    def test_an_unchecked_impression_stays_out_or_says_so(self) -> None:
        """A wrong fact confidently filed is worse than a missing one: a missing one gets asked about."""
        self.assertIn("a wrong fact confidently filed is worse than a missing one", self.page())

    def test_a_heading_is_an_anchor_so_renaming_one_breaks_citations(self) -> None:
        page = self.page()
        self.assertIn("renaming one breaks every citation", page)
        self.assertIn("the same rule the decision ids follow", page)


class SkipperCitationTest(unittest.TestCase):
    def brief(self) -> str:
        from slipwai.layout import AT_ROOT
        return flat(cruise_agents.cruise_body(AT_ROOT)[cruise_agents.SKIPPER])

    def test_the_skipper_reads_the_domain_before_deciding(self) -> None:
        self.assertIn(".specify/domain/", self.brief())

    def test_a_fact_it_decides_from_is_cited_with_file_heading_and_sentence(self) -> None:
        brief = self.brief()
        self.assertIn("cited, never summarised", brief)
        self.assertIn("quotes the sentence it turned on", brief)

    def test_a_paraphrase_is_refused_and_the_reason_is_given(self) -> None:
        """A paraphrase is the fact as somebody understood it, which is the thing a reader needs to check."""
        self.assertIn("a paraphrase is the fact as you understood it", self.brief().lower())

    def test_citing_nothing_is_written_down_rather_than_left_blank(self) -> None:
        """An absent citation and an unnecessary one look identical afterwards."""
        brief = self.brief()
        self.assertIn("`Cites: none`", brief)
        self.assertIn("only one of them is fine", brief)

    def test_the_point_is_checkability_and_the_brief_says_so(self) -> None:
        self.assertIn("answered from a guess about the domain cannot be told apart from it", self.brief())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
