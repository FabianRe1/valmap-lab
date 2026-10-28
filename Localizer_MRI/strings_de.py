"""Participant-facing texts of the MRI localizer, German (decided 2026-10-13).

Adapted from the old RepChanges localizer (loc_1_instruction_texts.py) to the space pictures.
Fields in braces are filled in by run_localizer.py.
"""

FOOTER_CONTINUE = "Weiter mit einer beliebigen Taste"

INSTRUCTIONS = [
    "Willkommen im Scanner!\n\n"
    "Bitte stelle sicher, dass du bequem liegst. Jetzt ist der letzte Moment, in dem du deine "
    "Position noch verändern kannst.",

    "Es ist wichtig, dass dein Kopf so still wie möglich liegt. Die Qualität der Daten leidet "
    "sehr unter Kopfbewegungen und könnte deine Daten für uns unbrauchbar machen.",

    "Die Aufgabe kennst du bereits.\n\n"
    "Wir zeigen dir nacheinander die Aliens, Raumschiffe, Planeten und Schätze. Schau dir jedes "
    "Bild aufmerksam an und halte es im Kopf.\n\n"
    "Ab und zu kommt ein Test mit zwei Bildern. Wähle das Bild, das zu dem Bild direkt davor "
    "passt. Das kann genau dasselbe Bild sein oder ein anderes Bild desselben Aliens, "
    "Raumschiffs, Planeten oder Schatzes.\n\n"
    "Rechter Zeigefinger: linkes Bild\n"
    "Rechter Mittelfinger: rechtes Bild\n"
    "Linker Zeigefinger: keines der beiden Bilder passt",
]

CHECK_INTRO = "Wir testen kurz die Tasten."
BUTTON_CHECK = {
    "check_left": "Bitte drücke die Taste unter deinem rechten Zeigefinger.\n\n(linkes Bild)",
    "check_right": "Bitte drücke die Taste unter deinem rechten Mittelfinger.\n\n(rechtes Bild)",
    "check_neither": "Bitte drücke die Taste unter deinem linken Zeigefinger.\n\n(keines der beiden Bilder)",
}

READY = ("Sehr gut, es kann losgehen.\n\n"
         "Wir melden uns nach jedem Block. Viel Erfolg!")

RESTARTED = ("Wir haben das Experiment neu gestartet.\n\n"
             "Wir machen weiter mit Block {block}. Die Daten werden wie geplant gespeichert.")

OPERATOR = "Block {block} von {n_blocks}\n\nWarten auf die Versuchsleitung ..."
WAIT_SCANNER = "Warten auf den Scanner ..."

TIMEOUT = "Zu langsam. Versuche, etwas schneller zu antworten."

BLOCK_DONE = ("Geschafft, ein Block ist vorbei!\n\n"
              "Du hast {done} % der Aufgabe abgeschlossen und {bonus} % des möglichen Bonus "
              "gesammelt.\n\n"
              "Ruh dich kurz aus und bleib dabei bitte ganz still liegen.")
BLOCK_DONE_RESTARTED = ("Geschafft, ein Block ist vorbei!\n\n"
                        "Du hast {done} % der Aufgabe abgeschlossen.\n\n"
                        "Ruh dich kurz aus und bleib dabei bitte ganz still liegen.")

GOODBYE = ("Glückwunsch, du hast diesen Teil abgeschlossen!\n\n"
           "Du hast {bonus} % des möglichen Bonus gesammelt.\n\n"
           "Bitte bleib noch still liegen, bis wir uns melden.")
