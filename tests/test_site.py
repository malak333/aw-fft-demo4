"""Unit tests for the FFT newcomer introduction page.

Uses only Python standard-library modules (unittest, html.parser).
Reads repository-local files directly — no server, subprocess, or
external dependencies required.
"""

import os
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = PROJECT_ROOT / "index.html"
STYLES_PATH = PROJECT_ROOT / "styles.css"

# ---------------------------------------------------------------------------
# Lightweight HTML parser
# ---------------------------------------------------------------------------

class _Element:
    """Represents a single parsed HTML element."""

    __slots__ = (
        "tag",
        "attrs",
        "parent_id",
        "parent_class",
        "parent_tag",
        "children",
        "text",
        "id",
        "classes",
        "depth",
    )

    def __init__(self, tag: str, attrs: list[tuple[str, str | None]], depth: int = 0):
        self.tag = tag
        self.attrs = attrs
        self.parent_id: str | None = None
        self.parent_class: str | None = None
        self.parent_tag: str | None = None
        self.children: list["_Element"] = []
        self.text: str = ""
        self.id: str | None = None
        self.classes: list[str] = []
        self.depth = depth
        for name, value in attrs:
            if name == "id" and value is not None:
                self.id = value
            if name == "class" and value is not None:
                self.classes = value.split()

    @property
    def attr_dict(self) -> dict[str, str | None]:
        return {name: value for name, value in self.attrs}

    @property
    def descendant_text(self) -> str:
        """Concatenated text of this element and all descendants."""
        texts: list[str] = [self.text]
        queue = list(self.children)
        while queue:
            child = queue.pop(0)
            texts.append(child.text)
            queue.extend(child.children)
        return " ".join(texts).strip()

    def _find_descendants(self, tag: str | None = None, text_contains: str | None = None) -> list["_Element"]:
        """BFS find all descendant elements matching criteria."""
        results: list["_Element"] = []
        queue = list(self.children)
        while queue:
            el = queue.pop(0)
            if tag is not None and el.tag != tag:
                queue.extend(el.children)
                continue
            if text_contains is not None and text_contains.lower() not in el.text.lower():
                queue.extend(el.children)
                continue
            results.append(el)
            queue.extend(el.children)
        return results


_VOID_TAGS = frozenset((
    "area", "base", "br", "col", "embed", "hr", "img",
    "input", "link", "meta", "source", "track", "wbr",
))


class _DocumentParser(HTMLParser):
    """Records tags, attributes, ancestry, text, IDs, fragments, and active resources.

    Uses a text buffer stack (one per element depth) so that text surrounding
    nested inline elements is not discarded.
    Void elements are not pushed onto the ancestry stack because they have
    no end tags.
    """

    def __init__(self) -> None:
        super().__init__()
        self._stack: list[_Element] = []
        self._roots: list[_Element] = []
        self._text_stack: list[list[str]] = []
        self._active_resources: list[tuple[str, str | None]] = []

    @property
    def roots(self) -> list[_Element]:
        return self._roots

    @property
    def active_resources(self) -> list[tuple[str, str | None]]:
        return list(self._active_resources)

    @property
    def all_elements(self) -> list[_Element]:
        """BFS traversal of the entire tree."""
        result: list[_Element] = []
        queue = list(self._roots)
        while queue:
            el = queue.pop(0)
            result.append(el)
            queue.extend(el.children)
        return result

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str]]) -> None:
        el = _Element(tag, attrs, depth=len(self._stack))
        if self._stack:
            parent = self._stack[-1]
            el.parent_tag = parent.tag
            el.parent_id = parent.id
            el.parent_class = " ".join(parent.classes)
            parent.children.append(el)
        else:
            self._roots.append(el)
        # Void elements have no end tag; record them but do not push onto the
        # ancestry stack so subsequent elements do not acquire false ancestry.
        if tag not in _VOID_TAGS:
            self._stack.append(el)
        self._text_stack.append([])

        # Track active resources — every script/img/iframe/embed/object is
        # active regardless of attributes; remote stylesheets are also active.
        if tag == "script":
            self._active_resources.append(("script", None))
        elif tag == "img":
            self._active_resources.append(("img", None))
        elif tag == "iframe":
            self._active_resources.append(("iframe", None))
        elif tag == "embed":
            self._active_resources.append(("embed", None))
        elif tag == "object":
            self._active_resources.append(("object", None))
        elif tag == "source":
            for attr_name, attr_val in attrs:
                if attr_name in ("src", "href") and attr_val is not None:
                    self._active_resources.append((tag, attr_val))
                    break
        elif tag == "link":
            attrs_dict = dict(attrs)
            if attrs_dict.get("rel") == "stylesheet":
                href = attrs_dict.get("href", "")
                if href and href.startswith("http"):
                    self._active_resources.append(("link", href))

    def handle_endtag(self, tag: str) -> None:
        if self._stack and self._stack[-1].tag == tag:
            el = self._stack.pop()
            el.text = "".join(self._text_stack.pop()).strip()

    def handle_data(self, data: str) -> None:
        if self._text_stack:
            self._text_stack[-1].append(data)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _parse_html() -> _DocumentParser:
    """Parse index.html and return the parser instance."""
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"{INDEX_PATH} not found")
    parser = _DocumentParser()
    parser.feed(INDEX_PATH.read_text(encoding="utf-8"))
    return parser


def _find(parser: _DocumentParser, tag: str | None = None, id_val: str | None = None,
          class_val: str | None = None, text_contains: str | None = None,
          parent_tag: str | None = None, parent_id: str | None = None) -> list[_Element]:
    """Return elements matching *tag*, optionally filtered by id, class, text, parent tag, or parent id."""
    results: list[_Element] = []
    for el in parser.all_elements:
        if tag is not None and el.tag != tag:
            continue
        if id_val is not None and el.id != id_val:
            continue
        if class_val is not None and class_val not in el.classes:
            continue
        if text_contains is not None and text_contains.lower() not in el.text.lower():
            continue
        if parent_tag is not None and el.parent_tag != parent_tag:
            continue
        if parent_id is not None and el.parent_id != parent_id:
            continue
        results.append(el)
    return results


def _fragment_targets(parser: _DocumentParser) -> set[str]:
    """All element IDs that can be resolved via fragment links."""
    return {el.id for el in parser.all_elements if el.id}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStructure(unittest.TestCase):
    """Semantic landmarks, skip link, sections, unique IDs, and resources."""

    def test_main_landmark_exists(self):
        parser = _parse_html()
        mains = _find(parser, tag="main")
        self.assertTrue(mains, "A <main> landmark must exist in the document.")

    def test_nav_landmark_exists(self):
        parser = _parse_html()
        navs = _find(parser, tag="nav")
        self.assertTrue(navs, "A <nav> landmark must exist in the document.")

    def test_skip_link_targets_main(self):
        parser = _parse_html()
        skip_links = _find(parser, tag="a", class_val="skip-link")
        self.assertTrue(skip_links, "An anchor with class 'skip-link' must exist.")
        href = skip_links[0].attr_dict.get("href", "")
        self.assertTrue(href.startswith("#"), "skip-link href must start with '#'")
        fragment = href[1:]
        self.assertEqual(fragment, "main", "skip-link href must resolve to the main landmark.")
        # Prove that #main resolves specifically to the actual <main> landmark
        mains = _find(parser, tag="main")
        main_ids = {m.id for m in mains}
        self.assertIn("main", main_ids, "The 'main' fragment must resolve to an actual <main> landmark.")

    def test_section_ids_inside_main(self):
        parser = _parse_html()
        required_ids = {"battles", "jobs", "ivalice", "characters"}
        sections_in_main = _find(parser, tag="section", parent_tag="main")
        actual_ids = {s.id for s in sections_in_main if s.id}
        missing = required_ids - actual_ids
        self.assertFalse(missing, f"Sections inside <main> must include IDs: {missing}")

    def test_unique_ids(self):
        parser = _parse_html()
        ids = [el.id for el in parser.all_elements if el.id]
        seen: dict[str, int] = {}
        for eid in ids:
            seen[eid] = seen.get(eid, 0) + 1
        duplicates = {k for k, v in seen.items() if v > 1}
        self.assertFalse(duplicates, f"IDs must be unique. Duplicates: {duplicates}")

    def test_fragments_resolve(self):
        parser = _parse_html()
        targets = _fragment_targets(parser)
        for el in _find(parser, tag="a"):
            href = el.attr_dict.get("href", "")
            if href.startswith("#"):
                fragment = href[1:]
                if not fragment:
                    self.fail(f"Anchor href='{href}' has an empty fragment target.")
                self.assertIn(fragment, targets,
                              f"Fragment link '{href}' must resolve to an existing element ID.")

    def test_exactly_one_local_stylesheet(self):
        parser = _parse_html()
        links = _find(parser, tag="link")
        local_links = [
            l for l in links
            if l.attr_dict.get("rel") == "stylesheet"
            and l.attr_dict.get("href")
            and not l.attr_dict["href"].startswith("http")
        ]
        self.assertEqual(len(local_links), 1,
                          "There must be exactly one active local stylesheet link.")
        self.assertEqual(local_links[0].attr_dict.get("href"), "styles.css",
                          "The stylesheet must reference local 'styles.css'.")

    def test_no_active_resources(self):
        parser = _parse_html()
        resources = parser.active_resources
        self.assertFalse(resources,
                          "No <script>, <img>, <iframe>, <embed>, <object>, <source>, or remote stylesheets expected.")


class TestCharacterProfiles(unittest.TestCase):
    """Character section must contain two profile articles with headings and text.

    Profiles must be direct children of <section id="characters"> so that moving
    them into another section (leaving #characters empty) causes failure.
    """

    def _get_parser(self) -> _DocumentParser:
        return _parse_html()

    def test_two_character_profiles(self):
        parser = self._get_parser()
        characters_section = _find(parser, tag="section", id_val="characters")
        self.assertTrue(characters_section, "<section id='characters'> must exist.")
        profiles = _find(parser, tag="article", class_val="character-profile",
                         parent_id="characters")
        self.assertEqual(len(profiles), 2,
                         "Exactly two <article class='character-profile'> expected inside #characters.")

    def test_ramza_profile(self):
        parser = self._get_parser()
        profiles = _find(parser, tag="article", class_val="character-profile",
                         parent_id="characters")
        ramza = [p for p in profiles if p.id == "ramza"]
        self.assertTrue(ramza, "A character-profile with id='ramza' must exist inside #characters.")
        headings = ramza[0]._find_descendants("h3", text_contains="Ramza Beoulve")
        self.assertTrue(headings,
                        "Ramza profile must contain a visible heading with the full name 'Ramza Beoulve'.")
        self.assertGreater(len(ramza[0].descendant_text), 50,
                           "Ramza profile must contain substantive text.")

    def test_delita_profile(self):
        parser = self._get_parser()
        profiles = _find(parser, tag="article", class_val="character-profile",
                         parent_id="characters")
        delita = [p for p in profiles if p.id == "delita"]
        self.assertTrue(delita, "A character-profile with id='delita' must exist inside #characters.")
        headings = delita[0]._find_descendants("h3", text_contains="Delita Hyral")
        self.assertTrue(headings,
                        "Delita profile must contain a visible heading with the full name 'Delita Hyral'.")
        self.assertGreater(len(delita[0].descendant_text), 50,
                           "Delita profile must contain substantive text.")

    def test_delita_commoner(self):
        parser = self._get_parser()
        profiles = _find(parser, tag="article", class_val="character-profile",
                         parent_id="characters")
        delita = [p for p in profiles if p.id == "delita"]
        self.assertTrue(delita, "Delita profile must exist inside #characters.")
        self.assertIn("commoner", delita[0].descendant_text.lower(),
                      "Delita's profile must identify him as a commoner.")


class TestBattlesFacts(unittest.TestCase):
    """Section-scoped factual guards for the battles section."""

    def _get_section_text(self) -> str:
        parser = _parse_html()
        sections = _find(parser, tag="section", id_val="battles")
        self.assertTrue(sections, "Section id='battles' must exist.")
        section_el = sections[0]
        texts: list[str] = []
        queue = list(section_el.children)
        while queue:
            el = queue.pop(0)
            texts.append(el.text)
            queue.extend(el.children)
        return " ".join(texts).lower()

    def test_speed_drives_ct(self):
        text = self._get_section_text()
        self.assertRegex(text, r"speed.*ct|ct.*speed",
                         "Battles must explain that Speed drives CT.")

    def test_ct_reaches_100(self):
        text = self._get_section_text()
        # Must connect CT to 100 and indicate the unit gains a turn
        self.assertRegex(text, r"ct.*100",
                         "Battles must connect CT to 100.")
        self.assertRegex(text, r"100.*(turn|act)|ct.*100.*(turn|act)",
                         "CT reaching 100 must mean the unit gains a turn.")

    def test_clock_ticks(self):
        text = self._get_section_text()
        self.assertRegex(text, r"clock tick",
                         "Battles must mention clock ticks driving CT accumulation.")

    def test_separate_charging(self):
        text = self._get_section_text()
        self.assertRegex(text, r"separate.*charge|charge.*separate|independent.*charge|charge.*independent",
                         "Battles must distinguish separately charged actions with independent timing.")

    def test_charging_between_turns(self):
        text = self._get_section_text()
        self.assertRegex(text, r"between.*turn|turn.*between",
                         "Separately charged actions must be able to resolve between unit turns.")

    def test_no_high_ground_bonuses(self):
        text = self._get_section_text()
        self.assertNotRegex(text, r"high.?ground.*bonus|bonus.*high.?ground",
                            "Battles must not assert blanket high-ground damage/defense bonuses.")

    def test_no_terrain_movement_costs(self):
        text = self._get_section_text()
        self.assertNotRegex(text, r"terrain.*cost|movement.*cost.*terrain",
                            "Battles must not assert generic terrain movement costs.")

    def test_no_cover_rules(self):
        text = self._get_section_text()
        self.assertNotRegex(text, r"cover",
                            "Battles must not assert cover rules.")

    def test_no_mandatory_move_plus_action(self):
        text = self._get_section_text()
        self.assertNotRegex(text, r"performs both movement and an action",
                            "Battles must not state a unit performs both movement and an action each turn.")

    def test_no_jump_as_job_granted(self):
        text = self._get_section_text()
        self.assertNotRegex(text, r"some jobs grant the jump statistic",
                            "Battles must not imply Jump is granted only by some jobs.")

    def test_move_jump_statistic(self):
        text = self._get_section_text()
        self.assertIn("move", text, "Battles must mention Move.")
        self.assertIn("jump", text, "Battles must mention Jump.")
        # Move must be described as horizontal movement range
        self.assertRegex(text, r"move.*horizontal|horizontal.*move",
                         "Move must be described as horizontal movement range.")
        # Jump must be described as governing elevation
        self.assertRegex(text, r"jump.*elevat|elevat.*jump",
                         "Jump must be described as governing elevation difference.")
        # Move and Jump must not be described as leaping over squares/enemies
        self.assertNotRegex(text, r"leap.?over|leap.*over.*square|leap.*enemy",
                            "Move and Jump must not be described as leaping over squares/enemies.")

    def test_elevation_and_facing(self):
        text = self._get_section_text()
        self.assertIn("elevat", text, "Battles must mention elevation.")
        self.assertIn("fac", text, "Battles must mention facing.")


class TestJobsFacts(unittest.TestCase):
    """Section-scoped factual guards for the jobs section."""

    def _get_section_text(self) -> str:
        parser = _parse_html()
        sections = _find(parser, tag="section", id_val="jobs")
        self.assertTrue(sections, "Section id='jobs' must exist.")
        section_el = sections[0]
        texts: list[str] = []
        queue = list(section_el.children)
        while queue:
            el = queue.pop(0)
            texts.append(el.text)
            queue.extend(el.children)
        return " ".join(texts).lower()

    def test_squire_foundational(self):
        text = self._get_section_text()
        self.assertIn("squire", text, "Jobs must mention Squire.")
        self.assertRegex(text, r"(squire.*(available|foundational)|(available|foundational).*squire|"
                            r"without.*prerequisite|no prerequisite|prerequisite.?free)",
                         "Squire must be described as available without prerequisites.")

    def test_chemist_foundational(self):
        text = self._get_section_text()
        self.assertIn("chemist", text, "Jobs must mention Chemist.")
        self.assertRegex(text, r"(chemist.*(available|foundational)|(available|foundational).*chemist|"
                            r"without.*prerequisite|no prerequisite|prerequisite.?free)",
                         "Chemist must be described as available without prerequisites.")

    def test_prerequisite_job_levels(self):
        text = self._get_section_text()
        self.assertRegex(text, r"prerequisite.*job.*level|job.*level.*prerequisite",
                         "Jobs must explain that advanced jobs unlock through prerequisite job levels.")

    def test_jp_purchases_abilities(self):
        text = self._get_section_text()
        self.assertRegex(text, r"jp.*(purchas|learn)|(purchas|learn).*jp",
                         "Jobs must state that JP buys/learns abilities.")

    def test_no_bravery_or_holy_site(self):
        text = self._get_section_text()
        self.assertNotRegex(text, r"bravery.*site|holy.*site",
                            "Jobs must not mention Bravery or Holy Site as job-switching locations.")

    def test_no_licenses_system(self):
        text = self._get_section_text()
        self.assertNotRegex(text, r"license\s*(tree|system|board)?",
                            "Jobs must not mention a Licenses system.")


class TestIvaliceFacts(unittest.TestCase):
    """Section-scoped factual guards for the Ivalice section."""

    def _get_section_text(self) -> str:
        parser = _parse_html()
        sections = _find(parser, tag="section", id_val="ivalice")
        self.assertTrue(sections, "Section id='ivalice' must exist.")
        section_el = sections[0]
        texts: list[str] = []
        queue = list(section_el.children)
        while queue:
            el = queue.pop(0)
            texts.append(el.text)
            queue.extend(el.children)
        return " ".join(texts).lower()

    def test_ivalice_is_kingdom(self):
        text = self._get_section_text()
        self.assertIn("kingdom", text,
                      "Ivalice must be described as a kingdom.")


class TestCharacterFacts(unittest.TestCase):
    """Section-scoped factual guards for the characters section."""

    def _get_section_text(self) -> str:
        parser = _parse_html()
        sections = _find(parser, tag="section", id_val="characters")
        self.assertTrue(sections, "Section id='characters' must exist.")
        section_el = sections[0]
        texts: list[str] = []
        queue = list(section_el.children)
        while queue:
            el = queue.pop(0)
            texts.append(el.text)
            queue.extend(el.children)
        return " ".join(texts).lower()

    def test_delita_commoner_identity(self):
        text = self._get_section_text()
        self.assertIn("commoner", text,
                      "Delita's profile must identify him as a commoner.")


class TestProhibitedMechanics(unittest.TestCase):
    """Global negative guards for invented or out-of-scope mechanics."""

    def test_no_weapon_triangles(self):
        parser = _parse_html()
        full_text = " ".join(el.text for el in parser.all_elements).lower()
        self.assertNotRegex(full_text, r"weapon.*triangle|triangle.*weapon",
                            "Must not mention weapon triangles.")

    def test_no_selectable_difficulty(self):
        parser = _parse_html()
        full_text = " ".join(el.text for el in parser.all_elements).lower()
        self.assertNotRegex(full_text, r"difficulty\s*(tier|select|level|option)?",
                            "Must not mention selectable difficulty tiers.")


class TestStylesheetExists(unittest.TestCase):
    """Verify styles.css exists and is referenced."""

    def test_styles_css_exists(self):
        self.assertTrue(STYLES_PATH.exists(), "styles.css must exist in the project root.")

    def test_styles_css_referenced(self):
        parser = _parse_html()
        links = _find(parser, tag="link")
        hrefs = [l.attr_dict.get("href") for l in links]
        self.assertIn("styles.css", hrefs, "index.html must reference 'styles.css'.")


if __name__ == "__main__":
    unittest.main()
