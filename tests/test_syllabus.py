"""Syllabus data and rules: each domain's topics, each role's focus, topic colour slots."""

from piq import resume_builder, syllabus
from piq.config import MAX_DOMAIN_TOPICS, TOPICS

EMBEDDED = "Embedded Systems & Firmware Engineer"


def test_every_domain_lists_aptitude_first_and_fits_the_palette():
    for d in syllabus.domains():
        assert d.topics[0] == "Aptitude", d.id
        assert len(d.topics) == len(set(d.topics)) <= MAX_DOMAIN_TOPICS, d.id
        assert d.core and set(d.core) <= set(d.topics)


def test_the_cs_core_is_the_original_six_topics_in_their_colour_order():
    cs = syllabus.domain("cs")
    assert cs.core == TOPICS and cs.topics[:6] == TOPICS


def test_every_catalog_role_has_a_skill_list_in_its_domain():
    known = syllabus.role_skills()
    for d in syllabus.domains():
        for role in d.roles:
            assert role in known, role  # the builder can onboard every role it offers
            assert {t for t in known[role].values() if t} <= set(d.topics), role


def test_an_embedded_engineer_practises_electronics_not_computer_science():
    # The reported bug: an ECE student saw DBMS, DSA and OOP as their weakest topics.
    assert syllabus.domain_of_role(EMBEDDED).id == "ece"
    focus = syllabus.focus_topics(EMBEDDED)
    assert focus == [
        "Aptitude",
        "Embedded C",
        "Microcontrollers",
        "Digital Electronics",
        "Communication Protocols",
        "RTOS",
    ]
    assert not set(focus) & {"DBMS", "OS", "CN", "DSA", "OOP"}


def test_tracked_topics_add_chosen_domain_topics_but_never_another_domains():
    tracked = syllabus.tracked_topics(EMBEDDED, {"VLSI & Verilog": 60.0, "DBMS": 0.0})
    assert "VLSI & Verilog" in tracked and "DBMS" not in tracked
    assert tracked == [t for t in syllabus.domain("ece").topics if t in tracked]  # domain order
    others = syllabus.other_topics(EMBEDDED, tracked)
    assert set(others) | set(tracked) == set(syllabus.domain("ece").topics)


def test_original_cs_roles_belong_to_cs_and_track_the_core():
    for role in ("Java Backend Developer", "Python Developer", "Data Analyst"):
        assert syllabus.domain_of_role(role).id == "cs"
    assert syllabus.focus_topics("Frontend Engineer")[-1] == "Web Development"
    assert set(syllabus.roles_in("cs")) >= {"Software Engineer", "Java Backend Developer"}


def test_colour_slots_follow_the_syllabus_position():
    assert syllabus.color_slot("Aptitude") == 0
    assert syllabus.color_slot("OS") == 2 and syllabus.color_slot("Embedded C") == 1
    assert syllabus.color_slot("Not a topic") is None
    domain = syllabus.color_domain(["OS", "Aptitude"])
    assert len(domain) == MAX_DOMAIN_TOPICS and domain[0] == "Aptitude" and domain[2] == "OS"
    # Placeholders fill the free slots and never match a topic name.
    assert all(d not in syllabus.all_topics() for d in domain if d not in ("OS", "Aptitude"))


def test_colour_slot_collisions_move_to_a_free_slot():
    domain = syllabus.color_domain(["Embedded C", "DBMS", "Mystery"])
    assert domain[1] == "Embedded C"  # first come keeps its slot
    assert "DBMS" in domain and domain.index("DBMS") != 1
    assert "Mystery" in domain
    assert len(set(domain)) == len(domain)


def test_skills_for_a_topic_come_from_the_role_map():
    assert syllabus.skills_for_topic(EMBEDDED, "Communication Protocols") == ["I2C", "SPI", "UART"]


def test_the_builder_reads_the_same_catalog():
    assert resume_builder.load_catalog() is syllabus.catalog()
