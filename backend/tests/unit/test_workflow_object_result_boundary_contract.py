from app.services.project_context_extractor import (
    project_context_extractor,
)


def boundary(
    sentence: str,
    action: str,
):
    occurrence = next(
        item
        for item
        in (
            project_context_extractor
            ._workflow_action_occurrences(
                sentence
            )
        )
        if item["action"] == action
    )

    match = occurrence["match"]

    return (
        project_context_extractor
        ._action_object(
            sentence,
            match,
        ),
        project_context_extractor
        ._result_after_action(
            sentence,
            match,
            occurrence["action"],
        ),
    )


def test_french_pour_article_noun_stays_in_object():
    object_text, result = boundary(
        (
            "Le fournisseur cr\u00e9e "
            "une annonce pour un \u00e9quipement."
        ),
        "creer",
    )

    assert object_text == (
        "une annonce pour un \u00e9quipement"
    )
    assert result == ""


def test_french_pour_bare_noun_stays_in_object():
    object_text, result = boundary(
        (
            "Le syst\u00e8me cr\u00e9e "
            "un dossier pour maintenance."
        ),
        "creer",
    )

    assert object_text == (
        "un dossier pour maintenance"
    )
    assert result == ""


def test_ambiguous_bare_pour_is_preserved_conservatively():
    object_text, result = boundary(
        (
            "Le syst\u00e8me cr\u00e9e une alerte "
            "pour informer l'op\u00e9rateur."
        ),
        "creer",
    )

    assert object_text == (
        "une alerte pour informer l'op\u00e9rateur"
    )
    assert result == ""


def test_french_pour_que_is_purpose():
    object_text, result = boundary(
        (
            "Le syst\u00e8me cr\u00e9e une alerte "
            "pour que le client puisse agir."
        ),
        "creer",
    )

    assert object_text == "une alerte"
    assert result == (
        "le client puisse agir"
    )


def test_french_afin_de_is_purpose():
    object_text, result = boundary(
        (
            "Le syst\u00e8me cr\u00e9e une alerte "
            "afin de r\u00e9duire le d\u00e9lai."
        ),
        "creer",
    )

    assert object_text == "une alerte"
    assert result == (
        "r\u00e9duire le d\u00e9lai"
    )


def test_english_in_order_to_is_purpose():
    object_text, result = boundary(
        (
            "The system creates a notification "
            "in order to inform the operator."
        ),
        "creer",
    )

    assert object_text == "a notification"
    assert result == (
        "inform the operator"
    )



def test_noun_ending_like_infinitive_is_not_purpose():
    object_text, result = boundary(
        (
            "Le syst\u00e8me cr\u00e9e "
            "une zone pour laser."
        ),
        "creer",
    )

    assert object_text == (
        "une zone pour laser"
    )
    assert result == ""


def test_another_infinitive_like_noun_is_not_purpose():
    object_text, result = boundary(
        (
            "Le syst\u00e8me cr\u00e9e "
            "un espace pour avenir."
        ),
        "creer",
    )

    assert object_text == (
        "un espace pour avenir"
    )
    assert result == ""
