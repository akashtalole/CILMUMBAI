"""SPEC-008 parts that need no services: redaction (AC7), language, agent definition (AC8)."""

from __future__ import annotations

from hishob.agentkit.definitions import load_agents
from hishob.agentkit.language import detect
from hishob.agentkit.redact import redact
from hishob.agentkit.tools import READ_ONLY_TOOLS, TOOL_DEFINITIONS


def test_spec008_ac7_phone_email_address_and_names_are_removed() -> None:
    text = "My name is Sunita Patil, call 98200 12345 or sunita@example.com. Flat No. 204, Gulmohar CHS."
    assert redact(text) == "My name is [name], call [phone] or [email]. [address], Gulmohar CHS."


def test_spec008_ac7_marathi_and_hindi_details_are_removed() -> None:
    assert redact("माझे नाव सुनीता पाटील आहे. फोन +91 98200-12345. खोली क्र. १२.") == (
        "माझे नाव [name] आहे. फोन [phone]. [address]."
    )
    assert redact("मेरा नाम रमेश यादव है, नंबर 9876543210।") == "मेरा नाम [name] है, नंबर [phone]।"


def test_spec008_ac7_landmarks_and_office_holders_stay() -> None:
    text = "Near Shri Ganesh Mandir; corporator Smt. Asha Mehta knows. श्री गणेश मंदिराजवळ नाला आहे."
    assert redact(text, keep=["Asha Mehta"]) == text


def test_language_detection() -> None:
    assert detect("एस. व्ही. रोडवरील खड्डा कोण दुरुस्त करणार आहे?") == "mr"
    assert detect("एस. वी. रोड का गड्ढा कौन ठीक करेगा?") == "hi"
    assert detect("Who will fix the pothole on S. V. Road?") == "en"


def test_spec008_ac8_the_desk_has_read_only_tools_no_delegation() -> None:
    config = load_agents()["citizen-desk"].config
    custom = [t for t in config["tools"] if t["type"] == "custom"]
    assert {t["name"] for t in custom} == READ_ONLY_TOOLS
    toolset = next(t for t in config["tools"] if t["type"] == "agent_toolset_20260401")
    assert toolset["default_config"]["enabled"] is False and not toolset.get("configs")
    assert "multiagent" not in config and "mcp_servers" not in config


def test_the_definition_file_and_the_code_describe_the_same_tools() -> None:
    config = load_agents()["citizen-desk"].config
    from_file = {t["name"]: t["input_schema"] for t in config["tools"] if t["type"] == "custom"}
    from_code = {t["name"]: t["input_schema"] for t in TOOL_DEFINITIONS}
    assert from_file == from_code


def test_spec008_common_words_that_begin_like_an_honorific_are_not_names() -> None:
    # Found by the SPEC-012 personal-data scan: कुछ (anything) and सौ (hundred) were redacted as names.
    assert redact("सहायक इंजीनियर कुछ न करें तो अगला कौन है?") == "सहायक इंजीनियर कुछ न करें तो अगला कौन है?"
    assert redact("ठेकेदाराला सौ रुपये दिले") == "ठेकेदाराला सौ रुपये दिले"
    assert redact("सौ. सुनीता पाटील यांनी तक्रार केली") == "सौ. [name] यांनी तक्रार केली"
    assert redact("कु. मीना आणि श्री रमेश पाटील") == "कु. [name] आणि श्री [name]"
