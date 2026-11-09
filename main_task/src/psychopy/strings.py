"""
Participant-facing text, English and German.

Mirrored by ../jspsych/strings.js. The main-task instructions state both change types outright
(experiment_spec.md section 6): both halves of the design are meant to be exploited, not
discovered. No text ever names cell ids, routes, or the word "grid" -- participants never see a
map of the task.
"""

import config as cfg

INSTRUCTION_SEQUENCE = [
    "instr_welcome",
    "instr_plan",               # 2026-10-02: what the introduction holds, then the task
    "instr_world",
    "instr_worth",
    "instr_short",
    "instr_value_change",
    "instr_structure_change",
    "instr_unseen",             # 2026-10-02: the unseen rest of a short trial's journey matters
    "instr_rest",
    "instr_probe",
    "instr_summary",
]

STRINGS = {
    "en": {
        # --- instructions -------------------------------------------------------------
        "instr_welcome": "Welcome, and thank you for taking part!\n\nIn this experiment you follow three aliens on their journeys through space: each alien boards a spaceship, the spaceship flies it to a planet, and on that planet a treasure waits. So each journey is a sequence of {n_clips} pictures (an alien, a spaceship, a planet) that always ends at a treasure.",
        # 2026-10-02: the plan of the introduction (the offline arm has no comprehension check)
        "instr_plan": (
            "HOW THE INTRODUCTION WORKS\n\nThe next screens explain everything you need to "
            "know.\n\n{intro_plan}"),
        "instr_world": "There are three journeys.\n\nEach journey starts with an alien. The alien boards a spaceship, the spaceship flies it to a planet, and on that planet a treasure waits: money, a gold relic, or a diamond. So every journey has the same order: first an alien, then a spaceship, then a planet, then the treasure.\n\nThere are three aliens, three spaceships and three planets, and each journey has its own alien, spaceship and planet.\n\nEach treasure waits at the end of a journey. When the journeys change (more on that below), a treasure always stays on its planet. You will get to know the three journeys before the main task starts.",
        "instr_worth": (
            "One journey is currently worth 100 points. The other two are worth 50 points "
            "each.\n\nWhen you watch a journey to its end, you see its treasure and how many "
            "points it is currently worth.\n\n"
            "Important: WHICH journey is worth 100 changes from time to time."),
        "instr_short": "Most trials show a whole journey: every picture from the first to the last, then its treasure and how many points it is worth.\n\nSome trials are SHORT, and there are two kinds. Some show only a treasure with its points, and no pictures at all: they are about the journey that currently ends at that treasure. Others show only two pictures in a row, and no treasure.\n\nA short trial can bring news, or it can simply show you something you already know. Nothing on the screen tells you which: only what you remember about the journeys does.",
        "instr_value_change": "When the 100 points move to another journey, you see a short trial with only a treasure and \"100\", and no pictures. The 100 now belongs to the journey that currently ends at this treasure.\n\nIf that journey was worth only 50 until now, the 100 has moved to it, and the journey that was worth 100 before is now worth only 50. If it was already worth 100, nothing has changed.\n\nNone of the journey's pictures are shown. Use what you know to work out which alien, spaceship and planet lead to this treasure right now.",
        "instr_structure_change": "The journeys themselves can also change: sometimes an alien boards a NEW spaceship, or a spaceship flies to a NEW planet.\n\nYou then see a short trial with just those two pictures in a row, and no treasure. If the second picture has always followed the first, nothing has changed. If it is new, this connection replaces the old one from now on: the two journeys involved swap their remaining parts. For example, if an alien now boards another alien's spaceship, that other alien takes over the first one's old spaceship. The treasures stay on their planets.\n\nYou only ever see one half of such a swap. The other half changes too, without being shown, and you will need to work out what it must now look like. These changes are permanent until another change happens.",
        # 2026-10-02: the unseen rest of a short trial's journey matters, and is asked about
        "instr_unseen": "WHAT YOU DO NOT SEE MATTERS\n\nEach journey has {n_clips} pictures. So when a short trial shows only two pictures in a row, the journey also has {pair_rest}. That part was not shown to you. It belongs to the same journey, and if the two pictures are a new connection, the unseen parts of both journeys involved have moved as well. A trial with only a treasure shows none of its journey's pictures: all of them are unseen.\n\nThe questions often ask about exactly these unseen parts: which pictures belong to the same journey right now, and what a change you saw only partly means for the rest. So pay close attention to every short trial, and use the pauses to work out what it means for the parts you did not see.",
        "instr_rest": "There are many longer pauses in the task, showing only a cross in the middle of the screen.\n\nUse these pauses to think about how things stand right now: which journey is worth 100, and which pictures belong to which journey. After a change, use them to work out what follows from it, for example which pictures the journey now worth 100 is made of, or what the half of a swap you were not shown must look like now.\n\nKeep your eyes on the cross the whole time. A BIGGER cross means that a new trial is about to start.",
        "instr_probe": (
            "From time to time you will be asked a question, with three pictures as possible "
            "answers.\n\nSome questions ask which picture you would prefer (choose a picture from the "
            "journey that is currently worth the most). Others show you one picture and ask which "
            "of the three pictures belongs to the same journey as that picture, that is, which one is "
            "part of the same sequence right now.\n\n"
            "Answer with the three response keys: left key = left picture, middle key = middle "
            "picture, right key = right picture. You have {t_probe:.0f} seconds. Answers always "
            "refer to how things are NOW, after all changes so far."),
        "instr_summary": "To sum up:\n\n1. Three journeys, each an alien, a spaceship and a planet, ending at that planet's treasure.\n2. One journey is worth 100, the others 50, and this changes.\n3. Connections can change; you see only half of each swap, and treasures stay on their planets.\n4. Short trials show only a treasure with its points, or only two pictures. They may bring news or not.\n5. In pauses, look at the cross and think through what is worth 100 and what belongs together now.\n6. Answer about the CURRENT state as well as you can.\n\n{practice_line}",
        # --- blocks -------------------------------------------------------------------
        "practice_intro": (
            "HOW IT WORKS\n\nFirst a short walkthrough with colored shapes. These shapes are NOT "
            "part of the main task: they are here only to show you how a journey works, what "
            "short trials look like, and what the two kinds of change look like.\n\nEach journey "
            "has its own color and always runs {shape_list}. Watch what happens to the treasure "
            "at the end and to the points. There is nothing to press."),
        "practice_note_same_value": (
            "That was a SHORT trial: a single YELLOW shape, then the YELLOW journey's banknotes "
            "with \"100\".\n\nThe YELLOW journey was already worth 100, so nothing has changed. Short"
            " trials often bring no news at all. Always compare what you see with what you "
            "already know."),
        # The two explanation screens shown straight after the practice changes. The colour words
        # must match config.PRACTICE_SHAPE_COLORS: journey 1 amber/yellow, 2 blue, 3 purple.
        "practice_note_value": (
            "Another short trial, and this time it brought news.\n\nIt showed a single BLUE shape, "
            "then the GOLD COINS with \"100\". The blue journey was worth only 50 until now, so the"
            " 100 points have moved: the blue journey is now worth 100, and the yellow one, worth"
            " 100 before, is now worth only 50.\n\nThe rest of the blue journey was not shown. You "
            "work it out from what you know."),
        "practice_note_same_structure": (
            "A short trial with two shapes in a row, then the PURPLE journey's diamonds with "
            "\"50\".\n\nThese two PURPLE shapes have always followed each other, so nothing has "
            "changed."),
        "practice_note_structure": (
            "Two shapes in a row again, but this time the connection is NEW: the YELLOW shape now"
            " leads to a PURPLE shape. From now on the YELLOW journey continues into the PURPLE "
            "one, so it now ends at the PURPLE journey's treasure, the diamonds.\n\nThat also tells"
            " you the other half, which you were NOT shown: the PURPLE journey must now continue "
            "into the YELLOW one. The two journeys swap their remaining parts, so working out the"
            " half you did not see is the whole point."),
        # The map screen after the structure note: both rewired journeys drawn start to finish
        # on one screen, the shown half above the inferred half. Same colour words as the note.
        "practice_map_structure": (
            "This is how the two journeys run now, from start to finish."),
        "practice_map_shown": "Shown to you: the YELLOW journey now continues into PURPLE",
        "practice_map_hidden": (
            "Not shown, but it follows: the PURPLE journey now continues into YELLOW"),
        "practice_done": (
            "Practice finished.\n\nPress {continue_key} to move on, or press P to repeat the "
            "practice."),
        "familiarization_intro": "THE THREE REAL JOURNEYS\n\nYou will now see the three real journeys of the main task, each one shown from start to finish with the treasure it ends at and the points it is worth.\n\nLearn which spaceship each alien boards, which planet each spaceship flies to, which treasure each journey ends at, and which journey is worth 100. The 100 stays on the same journey for the whole of this block, so you can learn it. Just watch; there is nothing to press.",
        "familiarization_done": "Done. Next come a few questions about what you just saw.",
        # the practice on the real journeys (2026-10-01)
        # what follows the instructions, on the welcome screen (2026-10-02)
        "intro_plan_real": "After these explanations, you get to know the three journeys and see examples that show what the task looks like, including both kinds of change.",
        "intro_plan_shapes": "After these explanations, a short practice with shapes shows how the task works.",
        "practice_line_shapes": "First, you will practice with shapes that are not part of the main task.",
        "practice_line_real": "First, you get to know the three journeys, and then you see examples of both kinds of change on them.",
        "familiarization_done_real": "Done. Next you see all three journeys on one screen, to learn them, and then examples of the changes on these journeys.",
        "practice_intro_real": "EXAMPLES OF THE CHANGES\n\nFirst you see all three journeys on one screen, to learn them. Then come short trials and both kinds of change as examples on these journeys. After each example, a screen shows the journeys involved and explains what happened. After the swap you answer three questions about it, with no time limit, and then see the right answers explained.\n\nThe examples are only practice: afterwards everything is reset to how you learned it.",
        "real_note_same_value": "That was a SHORT trial: only a treasure with \"100\", no pictures. The journey that ends at this treasure was already worth 100, so nothing has changed. Short trials often bring no news: always compare what you see with what you know.",
        "real_note_value": "Another short trial, and this time it brought news: this treasure with \"100\". The journey that ends at it was worth only 50 until now, so the 100 has moved to it, and the lower journey is now worth only 50. None of its pictures were shown: you work out from what you know which pictures lead to this treasure.",
        "real_label_value_new": "The journey that ends at this treasure: now worth 100",
        "real_label_value_old": "Worth 100 before, now worth only 50",
        "real_note_same_structure": "A short trial with only two pictures in a row, and no treasure. In this journey these two pictures have always followed each other, so nothing has changed.",
        "real_note_structure": "Two pictures in a row again, but this connection is NEW. The upper journey now continues into the end of another journey, so it now ends at that treasure. You were NOT shown the other half, but it follows: that other journey now continues into the upper journey's old end. The two swap their remaining parts.",
        "real_label_shown": "Shown to you: this journey now continues differently",
        "real_label_hidden": "Not shown, but it follows: this journey swaps its end too",
        "real_swap_explain": "WHAT A SWAP DOES\n\nYou can think of the journeys as paths that change their connections. Each frame outlines one journey. Before the change the frames run straight; after it they cross: the yellow journey now continues into the other one's end (this you were shown), and the blue journey into the yellow one's old end (this you had to work out).",
        "real_label_before": "BEFORE the change",
        "real_label_after": "AFTER the change",
        "real_reset": "THESE WERE ONLY EXAMPLES\n\nThe changes are undone. The journeys and their points are back exactly as you learned them, as shown below. The main task starts from here.",
        "names_intro_aliens": "MEET THE ALIENS\n\nThese are the three aliens of the task, each with its name.",
        "names_intro_spaceships": "THE SPACESHIPS\n\nThese are the three spaceships the aliens travel in.",
        "names_intro_planets": "THE PLANETS\n\nThese are the three planets the spaceships fly to. These screens do not show the journeys: which alien boards which spaceship, and where it flies, you see next.",
        "name_aliens_1": "Whale",
        "name_aliens_2": "Bird",
        "name_aliens_3": "Lizard",
        "name_spaceships_1": "Boat",
        "name_spaceships_2": "Car",
        "name_spaceships_3": "Rocket",
        "name_planets_1": "Volcano",
        "name_planets_2": "City",
        "name_planets_3": "Forest",
        "real_study": "LEARN THE JOURNEYS\n\nThese are the three journeys you just walked, each from start to finish with the treasure it ends at and the points it is worth. Everything that follows builds on them, so take as long as you need to learn them well. Continue when you feel comfortable with them.",
        "real_questions_intro": "THREE QUESTIONS ABOUT THIS SWAP\n\nThe two pictures you just saw were a NEW connection: a swap. The next three questions ask about parts of the journeys that this trial did NOT show, but that the swap changed. Work out what follows from it.\n\nTake your time: there is no time limit here. After each answer you see whether it was right, and afterwards the right answers are explained.",
        "real_answer_shown": "QUESTION {number} OF 3: THE RIGHT ANSWER\n\nThe right answer has the green frame. The picture at the top starts the journey you saw in the swap trial. That trial showed this journey continuing into a picture of another journey: a new connection. So from there on it runs along that other journey, all the way to its end.",
        "real_answer_hidden_next": "QUESTION {number} OF 3: THE RIGHT ANSWER\n\nThe right answer has the green frame. The picture at the top starts the OTHER journey of the swap, the one you were not shown. It follows anyway: its old continuation was taken over, so this journey now continues where the journey you saw used to go. The two journeys swap their remaining parts.",
        "real_answer_hidden_end": "QUESTION {number} OF 3: THE RIGHT ANSWER\n\nThe right answer has the green frame. Same journey as in question 2, the one you were not shown. From the swap on, it runs along the old remaining part of the journey you saw, so it now ends where that journey used to end.",
        "real_your_answer": "your answer",
        "real_no_answer": "You gave no answer to this question.",
        "gate_intro": (
            "A few questions about the journeys you just watched.\n\n"
            "There is no time limit here, and you will be told whether your answer was right. "
            "All answers refer to how things are RIGHT NOW."),
        "gate_passed": "All correct! The main task starts next.",
        "gate_failed": (
            "Not everything was correct yet.\n\nYou will see the journeys once more, and then "
            "the questions again."),
        "gate_exhausted": "Let's move on to the main task.",
        # The last intro screen: all three journeys on one screen with treasure and points.
        "structure_overview": (
            "THE STARTING POINT\n\nThese are the {n_journeys} journeys as they stand now, each "
            "from start to finish with the treasure it ends at and the points it is worth. "
            "From here on this keeps changing: journeys get rewired and the 100 moves, one "
            "change at a time, and you are only ever shown one part of each change."),
        "main_intro": (
            "The main task starts now. It is divided into {n_runs} parts with breaks in "
            "between.\n\nRemember: changes are permanent, you only ever see one half of each "
            "swap, and questions are about how things are NOW.\n\n{feedback_note}"),
        "feedback_note_on": "After each question you will be told whether you were right.",
        "feedback_note_off": "From here on there is no feedback.",
        # the label above the two change screens
        "break_screen": (
            "Part {run} of {n_runs} finished.\n\nTake a short break. Press the key when you "
            "are ready to continue."),
        # Shown before EVERY block, in every modality. One sentence: it names the key, and
        # outside the scanner the experimenter presses it. See config.TRIGGER_GATED_BLOCKS.
        "wait_trigger": (
            "Part {run} of {n_runs} is ready.\n\n"
            "The experiment waits for the trigger \"t\" to start."),
        "goodbye": "Finished! Thank you very much for taking part.",
        # the performance score (2026-10-02)
        "break_score": "In this part you answered {n_correct} of {n_questions} questions correctly.",
        "final_score": "You answered {n_correct} of {n_questions} questions correctly.",
        "aborted": "The session was stopped. Please contact the experimenter.",

        # --- probe prompts, one per probe_direction (spec section 5) --------------------
        "probe_preference": "Which of these do you prefer?",
        "probe_same_sequence": "Which of these pictures belongs to the same journey as this picture?",

        # --- feedback -----------------------------------------------------------------
        "feedback_correct": "Correct!",
        "feedback_wrong": "Wrong.",
        "feedback_none": "No answer recorded.",

        "press_space": "Press SPACE to continue",
        # the scanner (2026-10-26): any of the three buttons advances a screen
        "press_button": "Press any button to continue",
        # the lab sessions (MEG, MRI; 2026-10-26): a short refresher and a button check
        "lab_refresher_1": "A SHORT REMINDER\n\nYou already know the task from the online session. In brief:\n\n1. Three journeys, each an alien, a spaceship and a planet, ending at that planet's treasure.\n2. One journey is worth 100, the other two 50, and this changes during the task.\n3. Connections can change: two journeys swap their ends. You only ever see one half of each swap.",
        "lab_refresher_1b": "4. Short trials show only a treasure with its points, or only two pictures. They may bring news or not.\n5. In the pauses, look at the cross and think through what is worth 100 and what belongs together now.\n6. Questions are always about the CURRENT state.",
        "lab_refresher_2": "Today the journeys start again as you learned them. Which journey is worth 100 at the start may differ from last time: you will see it on an overview in a moment.\n\nYou answer with three buttons: left button = left picture, middle button = middle picture, right button = right picture. You have {t_probe} seconds.\n\nFirst, a short check of the buttons.",
        "button_check_left": "BUTTON CHECK\n\nPlace your fingers on the three buttons.\n\nNow press the LEFT button.",
        "button_check_middle": "Good. Now press the MIDDLE button.",
        "button_check_right": "Good. Now press the RIGHT button.",
        # the scanner (2026-11-04): the buttons by finger and color, worded as in RepChanges, the
        # lab's earlier study on the same scanner (config.MRI_OPTION_KEYS)
        "lab_refresher_2_mri": "Today the journeys start again as you learned them. Which journey is worth 100 at the start may differ from last time: you will see it on an overview in a moment.\n\nYou answer with three buttons:\nright index finger (blue) = left picture\nright middle finger (yellow) = right picture\nleft index finger = middle picture\nYou have {t_probe} seconds.\n\nFirst, a short check of the buttons.",
        "button_check_left_mri": "BUTTON CHECK\n\nPlease press the blue button under your right index finger.\n\n(left picture)",
        "button_check_middle_mri": "Good. Now the button under your left index finger.\n\n(middle picture)",
        "button_check_right_mri": "Good. Now the yellow button under your right middle finger.\n\n(right picture)",
        # the MEG response box (2026-11-05): the buttons by color, as the MEG localizer's check
        "lab_refresher_2_meg": "Today the journeys start again as you learned them. Which journey is worth 100 at the start may differ from last time: you will see it on an overview in a moment.\n\nYou answer with three buttons:\nleft (blue) button = left picture\nmiddle button = middle picture\nright (red) button = right picture\nYou have {t_probe} seconds.\n\nFirst, a short check of the buttons.",
        "button_check_left_meg": "BUTTON CHECK\n\nPlease press the left, blue button.\n\n(left picture)",
        "button_check_middle_meg": "Good. Now the middle button.\n\n(middle picture)",
        "button_check_right_meg": "Good. Now the right, red button.\n\n(right picture)",
        "button_check_done": "All set. Next you see the journeys as they stand at the start of this session.",
        # resuming after an interruption (--start-run R > 1, 2026-11-04): the state at the end of part R-1
        "button_check_done_resume": "All set. Next you see the journeys as they stand now, at the end of part {run}.",
        # the break overview's second press (2026-10-01)
        "press_space_again": "Press SPACE again to start the next part",
        "press_button_again": "Press a button again to start the next part",
        "break_overview": "WHERE THINGS STAND NOW\n\nThese are the {n_journeys} journeys as they stand at the end of part {run}, each from start to finish with the treasure it ends at and the points it is worth. Take a moment to compare this with what you had in mind. From here on it keeps changing again, one change at a time.",
    },

    "de": {
        "instr_welcome": "Willkommen und vielen Dank, dass du teilnimmst!\n\nIn diesem Experiment begleitest du drei Aliens auf ihren Reisen durch das All: Jedes Alien steigt in ein Raumschiff, das Raumschiff fliegt es zu einem Planeten, und auf diesem Planeten wartet ein Schatz. Jede Reise ist also eine Abfolge von {n_clips} Bildern (ein Alien, ein Raumschiff, ein Planet) und endet immer bei einem Schatz.",
        "instr_plan": (
            "SO LÄUFT DIE EINFÜHRUNG AB\n\nDie nächsten Bildschirme erklären alles, was du "
            "wissen musst.\n\n{intro_plan}"),
        "instr_world": "Es gibt drei Reisen.\n\nJede Reise beginnt mit einem Alien. Das Alien steigt in ein Raumschiff, das Raumschiff fliegt es zu einem Planeten, und auf diesem Planeten wartet ein Schatz: Geld, ein goldenes Relikt oder ein Diamant. Jede Reise hat also dieselbe Reihenfolge: zuerst ein Alien, dann ein Raumschiff, dann ein Planet, dann der Schatz.\n\nEs gibt drei Aliens, drei Raumschiffe und drei Planeten, und jede Reise hat ihr eigenes Alien, Raumschiff und ihren eigenen Planeten.\n\nJeder Schatz wartet am Ende einer Reise. Wenn sich die Reisen ändern (mehr dazu unten), bleibt ein Schatz immer auf seinem Planeten. Du lernst die drei Reisen vor der Hauptaufgabe kennen.",
        "instr_worth": (
            "Eine Reise ist aktuell 100 Punkte wert. Die anderen beiden sind je 50 Punkte "
            "wert.\n\nWenn du eine Reise bis zum Ende siehst, siehst du ihren Schatz und wie "
            "viele Punkte sie gerade wert ist.\n\n"
            "Wichtig: WELCHE Reise 100 Punkte wert ist, ändert sich von Zeit zu Zeit."),
        "instr_short": "Die meisten Durchgänge zeigen eine ganze Reise: jedes Bild vom ersten bis zum letzten, dann ihren Schatz und wie viele Punkte sie wert ist.\n\nManche Durchgänge sind KURZ, und es gibt zwei Arten. Manche zeigen nur einen Schatz mit seinen Punkten und gar keine Bilder: Sie betreffen die Reise, die gerade bei diesem Schatz endet. Andere zeigen nur zwei Bilder hintereinander und keinen Schatz.\n\nEin kurzer Durchgang kann etwas Neues zeigen oder einfach etwas, das du schon weißt. Auf dem Bildschirm siehst du nicht, was davon zutrifft: Das verrät dir nur dein Wissen über die Reisen.",
        "instr_value_change": "Wenn die 100 Punkte zu einer anderen Reise wandern, siehst du einen kurzen Durchgang mit nur einem Schatz und \"100\", ohne Bilder. Die 100 gehören jetzt zu der Reise, die gerade bei diesem Schatz endet.\n\nWar diese Reise bisher nur 50 wert, sind die 100 Punkte zu ihr gewandert, und die Reise, die vorher 100 wert war, ist jetzt nur noch 50 wert. War sie schon 100 wert, hat sich nichts geändert.\n\nKeines der Bilder dieser Reise wird gezeigt. Nutze dein Wissen, um herauszufinden, welches Alien, welches Raumschiff und welcher Planet gerade zu diesem Schatz führen.",
        "instr_structure_change": "Auch die Reisen selbst können sich ändern: Manchmal steigt ein Alien in ein NEUES Raumschiff, oder ein Raumschiff fliegt zu einem NEUEN Planeten.\n\nDann siehst du einen kurzen Durchgang mit nur diesen beiden Bildern hintereinander und keinem Schatz. Folgte das zweite Bild schon immer auf das erste, hat sich nichts geändert. Ist es neu, ersetzt diese Verbindung ab jetzt die alte: Die beiden beteiligten Reisen tauschen ihre restlichen Teile. Steigt zum Beispiel ein Alien jetzt in das Raumschiff eines anderen Aliens, übernimmt dieses andere Alien das alte Raumschiff des ersten. Die Schätze bleiben auf ihren Planeten.\n\nDu siehst immer nur eine Hälfte eines solchen Tauschs. Die andere Hälfte ändert sich ebenfalls, ohne gezeigt zu werden, und du musst erschließen, wie sie jetzt aussehen muss. Diese Änderungen bleiben bestehen, bis sich wieder etwas ändert.",
        "instr_unseen": "WAS DU NICHT SIEHST, ZÄHLT\n\nJede Reise besteht aus {n_clips} Bildern. Wenn ein kurzer Durchgang also nur zwei Bilder hintereinander zeigt, hat die Reise noch {pair_rest}. Dieser Teil wurde dir nicht gezeigt. Er gehört zur selben Reise, und ist die Verbindung der beiden Bilder neu, haben sich auch die ungesehenen Teile beider beteiligten Reisen verschoben. Ein Durchgang mit nur einem Schatz zeigt keines der Bilder seiner Reise: Sie sind alle ungesehen.\n\nDie Fragen beziehen sich oft genau auf diese ungesehenen Teile: welche Bilder gerade zur selben Reise gehören und was eine Änderung, die du nur zum Teil gesehen hast, für den Rest bedeutet. Achte deshalb genau auf jeden kurzen Durchgang, und nutze die Pausen, um zu erschließen, was er für die nicht gezeigten Teile bedeutet.",
        "instr_rest": "In der Aufgabe gibt es viele längere Pausen, in denen nur ein Kreuz in der Bildschirmmitte zu sehen ist.\n\nNutze diese Pausen, um darüber nachzudenken, wie die Dinge gerade stehen: welche Reise 100 wert ist und welche Bilder zu welcher Reise gehören. Nach einer Änderung nutzt du sie, um herauszufinden, was daraus folgt, zum Beispiel aus welchen Bildern die Reise besteht, die jetzt 100 wert ist, oder wie die nicht gezeigte Hälfte eines Tauschs jetzt aussehen muss.\n\nSchau dabei die ganze Zeit auf das Kreuz. Ein GRÖSSERES Kreuz bedeutet, dass gleich ein neuer Durchgang beginnt.",
        "instr_probe": (
            "Von Zeit zu Zeit wird dir eine Frage gestellt, mit drei Bildern als möglichen "
            "Antworten.\n\nManche Fragen fragen, welches Bild du bevorzugst (wähle ein "
            "Bild der Reise, die gerade am meisten wert ist). Andere zeigen dir ein Bild und "
            "fragen, welches der drei Bilder zur selben Reise gehört wie dieses, also gerade Teil "
            "derselben Abfolge ist.\n\n"
            "Antworte mit den drei Antworttasten: linke Taste = linkes Bild, mittlere "
            "Taste = mittleres Bild, rechte Taste = rechtes Bild. Du hast {t_probe:.0f} "
            "Sekunden. Antworten beziehen sich immer auf den JETZIGEN Stand, nach allen "
            "bisherigen Änderungen."),
        "instr_summary": "Zusammengefasst:\n\n1. Drei Reisen, jede aus einem Alien, einem Raumschiff und einem Planeten, die beim Schatz dieses Planeten endet.\n2. Eine Reise ist 100 wert, die anderen 50, und das ändert sich.\n3. Verbindungen können sich ändern; du siehst nur die Hälfte jedes Tauschs, und Schätze bleiben auf ihren Planeten.\n4. Kurze Durchgänge zeigen nur einen Schatz mit seinen Punkten oder nur zwei Bilder. Sie können etwas Neues zeigen oder nicht.\n5. Schau in den Pausen auf das Kreuz und denk durch, was 100 wert ist und was jetzt zusammengehört.\n6. Antworte zum AKTUELLEN Stand, so gut du kannst.\n\n{practice_line}",
        "practice_intro": (
            "SO FUNKTIONIERT ES\n\nZuerst ein kurzer Durchgang mit farbigen Formen. Diese Formen "
            "gehören NICHT zur Hauptaufgabe: Sie zeigen nur, wie eine Reise aufgebaut ist, wie "
            "kurze Durchgänge aussehen und wie die beiden Arten von Änderung aussehen.\n\nJede "
            "Reise hat ihre eigene Farbe und läuft immer {shape_list}. Achte darauf, was "
            "mit dem Schatz am Ende und mit den Punkten passiert. Du musst nichts drücken."),
        "practice_note_same_value": (
            "Das war ein KURZER Durchgang: eine einzelne GELBE Form, dann die Geldscheine der "
            "GELBEN Reise mit \"100\".\n\nDie GELBE Reise war schon 100 wert, also hat sich nichts "
            "geändert. Kurze Durchgänge bringen oft gar nichts Neues. Vergleiche immer, "
            "was du siehst, mit dem, was du schon weißt."),
        "practice_note_value": (
            "Wieder ein kurzer Durchgang, und diesmal mit einer Neuigkeit.\n\nEr zeigte eine "
            "einzelne BLAUE Form, dann die GOLDMÜNZEN mit \"100\". Die blaue Reise war bisher nur "
            "50 wert, also sind die 100 Punkte gewandert: Die blaue Reise ist jetzt 100 wert, und"
            " die gelbe, die vorher 100 wert war, nur noch 50.\n\nDer Rest der blauen Reise wurde "
            "nicht gezeigt. Den erschließt du aus deinem Wissen."),
        "practice_note_same_structure": (
            "Ein kurzer Durchgang mit zwei Formen hintereinander, dann die Diamanten der LILA "
            "Reise mit \"50\".\n\nDiese beiden LILA Formen folgten schon immer aufeinander, also hat "
            "sich nichts geändert."),
        "practice_note_structure": (
            "Wieder zwei Formen hintereinander, aber diesmal ist die Verbindung NEU: Die GELBE "
            "Form führt jetzt zu einer LILA Form. Ab jetzt führt die GELBE Reise in die LILA "
            "Reise und endet deshalb beim Schatz der LILA Reise, den Diamanten.\n\nDamit kennst du"
            " auch die andere Hälfte, die NICHT gezeigt wurde: Die LILA Reise muss jetzt in die "
            "GELBE führen. Die beiden Reisen tauschen ihre restlichen Teile, und genau diese "
            "nicht gezeigte Hälfte selbst zu erschließen ist die Aufgabe."),
        "practice_map_structure": (
            "So verlaufen die beiden Reisen jetzt, von Anfang bis Ende."),
        "practice_map_shown": "Gezeigt: Die GELBE Reise führt jetzt in die LILA Reise",
        "practice_map_hidden": (
            "Nicht gezeigt, aber daraus folgt: Die LILA Reise führt jetzt in die GELBE Reise"),
        "practice_done": (
            "Übung beendet.\n\nDrücke {continue_key}, um weiterzumachen, oder P, um die "
            "Übung zu wiederholen."),
        "familiarization_intro": "DIE DREI ECHTEN REISEN\n\nDu siehst jetzt die drei echten Reisen der Hauptaufgabe, jede einmal von Anfang bis Ende, mit dem Schatz am Ende und den Punkten, die sie wert ist.\n\nLerne, in welches Raumschiff jedes Alien steigt, zu welchem Planeten jedes Raumschiff fliegt, bei welchem Schatz jede Reise endet und welche Reise 100 wert ist. Die 100 bleibt in diesem Block bei derselben Reise, damit du sie lernen kannst. Nur zuschauen; du musst nichts drücken.",
        "familiarization_done": "Fertig. Es folgen einige Fragen zu dem, was du gesehen hast.",
        # the practice on the real journeys (2026-10-01)
        "intro_plan_real": "Nach diesen Erklärungen lernst du die drei Reisen kennen und siehst Beispiele, die zeigen, wie die Aufgabe aussieht, auch für beide Arten von Änderung.",
        "intro_plan_shapes": "Nach diesen Erklärungen zeigt eine kurze Übung mit Formen, wie die Aufgabe funktioniert.",
        "practice_line_shapes": "Zuerst übst du mit Formen, die nicht zur Hauptaufgabe gehören.",
        "practice_line_real": "Zuerst lernst du die drei Reisen kennen, und dann siehst du an ihnen Beispiele für beide Arten von Änderung.",
        "familiarization_done_real": "Fertig. Als Nächstes siehst du alle drei Reisen auf einem Bildschirm, um sie zu lernen, und dann Beispiele für die Änderungen an diesen Reisen.",
        "practice_intro_real": "BEISPIELE FÜR DIE ÄNDERUNGEN\n\nZuerst siehst du alle drei Reisen auf einem Bildschirm, um sie zu lernen. Dann folgen kurze Durchgänge und beide Arten von Änderung als Beispiele an diesen Reisen. Nach jedem Beispiel zeigt ein Bildschirm die beteiligten Reisen und erklärt, was passiert ist. Nach dem Tausch beantwortest du drei Fragen dazu, ohne Zeitlimit, und siehst danach die richtigen Antworten erklärt.\n\nDie Beispiele sind nur Übung: Danach wird alles wieder so, wie du es gelernt hast.",
        "real_note_same_value": "Das war ein KURZER Durchgang: nur ein Schatz mit \"100\", keine Bilder. Die Reise, die bei diesem Schatz endet, war schon 100 wert, also hat sich nichts geändert. Kurze Durchgänge bringen oft nichts Neues: Vergleiche immer, was du siehst, mit dem, was du weißt.",
        "real_note_value": "Noch ein kurzer Durchgang, und diesmal mit einer Neuigkeit: dieser Schatz mit \"100\". Die Reise, die bei ihm endet, war bisher nur 50 wert, also sind die 100 zu ihr gewandert, und die untere Reise ist jetzt nur noch 50 wert. Keines ihrer Bilder wurde gezeigt: Du erschließt aus dem, was du weißt, welche Bilder zu diesem Schatz führen.",
        "real_label_value_new": "Die Reise, die bei diesem Schatz endet: jetzt 100 wert",
        "real_label_value_old": "Vorher 100 wert, jetzt nur noch 50",
        "real_note_same_structure": "Ein kurzer Durchgang mit nur zwei Bildern hintereinander und keinem Schatz. In dieser Reise folgten diese beiden Bilder schon immer aufeinander, also hat sich nichts geändert.",
        "real_note_structure": "Wieder zwei Bilder hintereinander, aber diese Verbindung ist NEU. Die obere Reise führt jetzt in das Ende einer anderen Reise weiter und endet deshalb jetzt bei deren Schatz. Die andere Hälfte wurde dir NICHT gezeigt, aber sie folgt daraus: Jene andere Reise führt jetzt in das alte Ende der oberen Reise weiter. Die beiden tauschen ihre restlichen Teile.",
        "real_label_shown": "Gezeigt: Diese Reise geht jetzt anders weiter",
        "real_label_hidden": "Nicht gezeigt, aber es folgt: Diese Reise tauscht ihr Ende ebenfalls",
        "real_swap_explain": "WAS EIN TAUSCH BEWIRKT\n\nDu kannst dir die Reisen als Wege vorstellen, die ihre Verbindungen ändern. Jeder Rahmen umfasst eine Reise. Vor der Änderung verlaufen die Rahmen gerade, danach kreuzen sie sich: Die gelbe Reise führt jetzt in das Ende der anderen weiter (das wurde dir gezeigt), die blaue Reise in das alte Ende der gelben (das musstest du erschließen).",
        "real_label_before": "VOR der Änderung",
        "real_label_after": "NACH der Änderung",
        "real_reset": "DAS WAREN NUR BEISPIELE\n\nDie Änderungen sind rückgängig gemacht. Die Reisen und ihre Punkte sind wieder genau so, wie du sie gelernt hast, wie unten gezeigt. Hier beginnt die Hauptaufgabe.",
        "names_intro_aliens": "DIE ALIENS\n\nDas sind die drei Aliens der Aufgabe, jedes mit seinem Namen.",
        "names_intro_spaceships": "DIE RAUMSCHIFFE\n\nDas sind die drei Raumschiffe, mit denen die Aliens reisen.",
        "names_intro_planets": "DIE PLANETEN\n\nDas sind die drei Planeten, zu denen die Raumschiffe fliegen. Diese Bildschirme zeigen nicht die Reisen: In welches Raumschiff welches Alien steigt und wohin es fliegt, siehst du als Nächstes.",
        "name_aliens_1": "Wal",
        "name_aliens_2": "Vogel",
        "name_aliens_3": "Echse",
        "name_spaceships_1": "Boot",
        "name_spaceships_2": "Auto",
        "name_spaceships_3": "Rakete",
        "name_planets_1": "Vulkan",
        "name_planets_2": "Stadt",
        "name_planets_3": "Wald",
        "real_study": "LERNE DIE REISEN\n\nDas sind die drei Reisen, die du gerade gegangen bist, jede von Anfang bis Ende mit dem Schatz, bei dem sie endet, und den Punkten, die sie wert ist. Alles Weitere baut darauf auf, nimm dir also so viel Zeit, wie du brauchst, um sie gut zu lernen. Mach weiter, wenn du dich sicher fühlst.",
        "real_questions_intro": "DREI FRAGEN ZU DIESEM TAUSCH\n\nDie zwei Bilder, die du gerade gesehen hast, waren eine NEUE Verbindung: ein Tausch. Die nächsten drei Fragen betreffen Teile der Reisen, die dieser Durchgang NICHT gezeigt hat, die der Tausch aber verändert hat. Erschließe, was daraus folgt.\n\nNimm dir Zeit: Hier gibt es kein Zeitlimit. Nach jeder Antwort siehst du, ob sie richtig war, und danach werden die richtigen Antworten erklärt.",
        "real_answer_shown": "FRAGE {number} VON 3: DIE RICHTIGE ANTWORT\n\nDie richtige Antwort hat den grünen Rahmen. Das Bild oben beginnt die Reise, die du im Tausch-Durchgang gesehen hast. Dieser Durchgang zeigte, wie die Reise in ein Bild einer anderen Reise weiterführt: eine neue Verbindung. Von dort an verläuft sie also entlang dieser anderen Reise, bis zu deren Ende.",
        "real_answer_hidden_next": "FRAGE {number} VON 3: DIE RICHTIGE ANTWORT\n\nDie richtige Antwort hat den grünen Rahmen. Das Bild oben beginnt die ANDERE Reise des Tauschs, die dir nicht gezeigt wurde. Es folgt trotzdem: Ihre alte Fortsetzung wurde übernommen, also führt diese Reise jetzt dorthin weiter, wohin die gesehene Reise früher ging. Die beiden Reisen tauschen ihre restlichen Teile.",
        "real_answer_hidden_end": "FRAGE {number} VON 3: DIE RICHTIGE ANTWORT\n\nDie richtige Antwort hat den grünen Rahmen. Dieselbe Reise wie in Frage 2, die dir nicht gezeigt wurde. Ab dem Tausch verläuft sie entlang des alten restlichen Teils der gesehenen Reise und endet deshalb jetzt dort, wo jene Reise früher endete.",
        "real_your_answer": "Deine Antwort",
        "real_no_answer": "Du hast diese Frage nicht beantwortet.",
        "gate_intro": (
            "Einige Fragen zu den Reisen, die du gerade gesehen hast.\n\n"
            "Hier gibt es kein Zeitlimit, und du erfährst, ob deine Antwort richtig war. Alle "
            "Antworten beziehen sich auf den JETZIGEN Stand."),
        "gate_passed": "Alles richtig! Als Nächstes beginnt die Hauptaufgabe.",
        "gate_failed": (
            "Noch nicht alles war richtig.\n\nDu siehst die Reisen noch einmal und danach "
            "wieder die Fragen."),
        "gate_exhausted": "Weiter geht es mit der Hauptaufgabe.",
        "structure_overview": (
            "DER AUSGANGSPUNKT\n\nSo stehen die {n_journeys} Reisen jetzt, jede von Anfang bis "
            "Ende mit dem Schatz am Ende und den Punkten, die sie wert ist. Ab jetzt ändert sich "
            "das laufend: Reisen werden umgebaut und die 100 wandert, immer eine Änderung nach "
            "der anderen, und du siehst jeweils nur einen Teil jeder Änderung."),
        "main_intro": (
            "Jetzt beginnt die Hauptaufgabe. Sie ist in {n_runs} Teile mit Pausen dazwischen "
            "gegliedert.\n\nDenk daran: Änderungen bleiben bestehen, du siehst immer nur "
            "eine Hälfte jedes Tauschs, und die Fragen beziehen sich auf den JETZIGEN "
            "Stand.\n\n{feedback_note}"),
        "feedback_note_on": "Nach jeder Frage erfährst du, ob deine Antwort richtig war.",
        "feedback_note_off": "Ab jetzt gibt es keine Rückmeldung mehr.",
        "break_screen": (
            "Teil {run} von {n_runs} geschafft.\n\nMach eine kurze Pause. Drücke "
            "die Taste, wenn du bereit bist."),
        "wait_trigger": (
            "Teil {run} von {n_runs} ist bereit.\n\n"
            "Das Experiment wartet auf den Trigger \"t\", um zu starten."),
        "goodbye": "Geschafft! Vielen Dank für deine Teilnahme.",
        "break_score": "In diesem Teil hast du {n_correct} von {n_questions} Fragen richtig beantwortet.",
        "final_score": "Du hast {n_correct} von {n_questions} Fragen richtig beantwortet.",
        "aborted": "Die Sitzung wurde abgebrochen. Bitte wende dich an die Versuchsleitung.",

        "probe_preference": "Welches dieser Bilder bevorzugst du?",
        "probe_same_sequence": "Welches dieser Bilder gehört zur selben Reise wie dieses Bild?",

        "feedback_correct": "Richtig!",
        "feedback_wrong": "Falsch.",
        "feedback_none": "Keine Antwort registriert.",

        "press_space": "Weiter mit der LEERTASTE",
        "press_button": "Weiter mit einer der Tasten",
        "lab_refresher_1": "KURZE WIEDERHOLUNG\n\nDu kennst die Aufgabe schon aus der Online-Sitzung. Zur Erinnerung:\n\n1. Drei Reisen, jede aus einem Alien, einem Raumschiff und einem Planeten, die beim Schatz dieses Planeten endet.\n2. Eine Reise ist 100 wert, die anderen beiden 50, und das ändert sich im Lauf der Aufgabe.\n3. Verbindungen können sich ändern: Zwei Reisen tauschen ihre Enden. Du siehst immer nur eine Hälfte jedes Tauschs.",
        "lab_refresher_1b": "4. Kurze Durchgänge zeigen nur einen Schatz mit seinen Punkten oder nur zwei Bilder. Sie können etwas Neues zeigen oder nicht.\n5. Schau in den Pausen auf das Kreuz und denk durch, was jetzt 100 wert ist und was zusammengehört.\n6. Die Fragen beziehen sich immer auf den AKTUELLEN Stand.",
        "lab_refresher_2": "Heute beginnen die Reisen wieder so, wie du sie gelernt hast. Welche Reise am Anfang 100 wert ist, kann aber anders sein als beim letzten Mal: Das siehst du gleich auf einer Übersicht.\n\nDu antwortest mit drei Tasten: linke Taste = linkes Bild, mittlere Taste = mittleres Bild, rechte Taste = rechtes Bild. Du hast {t_probe} Sekunden Zeit.\n\nZuerst prüfen wir kurz die Tasten.",
        "button_check_left": "TASTEN-CHECK\n\nLeg deine Finger auf die drei Tasten.\n\nDrücke jetzt die LINKE Taste.",
        "button_check_middle": "Gut. Drücke jetzt die MITTLERE Taste.",
        "button_check_right": "Gut. Drücke jetzt die RECHTE Taste.",
        "lab_refresher_2_mri": "Heute beginnen die Reisen wieder so, wie du sie gelernt hast. Welche Reise am Anfang 100 wert ist, kann aber anders sein als beim letzten Mal: Das siehst du gleich auf einer Übersicht.\n\nDu antwortest mit drei Tasten:\nrechter Zeigefinger (blau) = linkes Bild\nrechter Mittelfinger (gelb) = rechtes Bild\nlinker Zeigefinger = mittleres Bild\nDu hast {t_probe} Sekunden Zeit.\n\nZuerst prüfen wir kurz die Tasten.",
        "button_check_left_mri": "TASTEN-CHECK\n\nBitte drücke die blaue Taste unter deinem rechten Zeigefinger.\n\n(linkes Bild)",
        "button_check_middle_mri": "Gut. Jetzt die Taste unter deinem linken Zeigefinger.\n\n(mittleres Bild)",
        "button_check_right_mri": "Gut. Jetzt die gelbe Taste unter deinem rechten Mittelfinger.\n\n(rechtes Bild)",
        "lab_refresher_2_meg": "Heute beginnen die Reisen wieder so, wie du sie gelernt hast. Welche Reise am Anfang 100 wert ist, kann aber anders sein als beim letzten Mal: Das siehst du gleich auf einer Übersicht.\n\nDu antwortest mit drei Tasten:\nlinke (blaue) Taste = linkes Bild\nmittlere Taste = mittleres Bild\nrechte (rote) Taste = rechtes Bild\nDu hast {t_probe} Sekunden Zeit.\n\nZuerst prüfen wir kurz die Tasten.",
        "button_check_left_meg": "TASTEN-CHECK\n\nBitte drücke die linke, blaue Taste.\n\n(linkes Bild)",
        "button_check_middle_meg": "Gut. Jetzt die mittlere Taste.\n\n(mittleres Bild)",
        "button_check_right_meg": "Gut. Jetzt die rechte, rote Taste.\n\n(rechtes Bild)",
        "button_check_done": "Alles bereit. Gleich siehst du die Reisen, wie sie zu Beginn dieser Sitzung stehen.",
        "button_check_done_resume": "Alles bereit. Gleich siehst du die Reisen, wie sie jetzt stehen, am Ende von Teil {run}.",
        "press_space_again": "Noch einmal die LEERTASTE, um den nächsten Teil zu starten",
        "press_button_again": "Noch einmal eine der Tasten, um den nächsten Teil zu starten",
        "break_overview": "DER AKTUELLE STAND\n\nSo stehen die {n_journeys} Reisen am Ende von Teil {run}, jede von Anfang bis Ende mit dem Schatz, bei dem sie endet, und den Punkten, die sie wert ist. Nimm dir einen Moment, um das mit deinem Bild der Reisen zu vergleichen. Ab jetzt ändert es sich wieder, eine Änderung nach der anderen.",
    },
}


# The one prompt table, keyed by the schedule's probe_direction. Mirrored by ../jspsych/strings.js.
PROBE_PROMPT_KEYS = {
    "preference": "probe_preference",
    "same_sequence": "probe_same_sequence",
}


# Wording that follows the route-length knob. The instructions and the practice introduction have
# to state the ACTUAL number of clips in a journey and the ACTUAL shape sequence, otherwise the
# 3-step variant tells participants something the task then contradicts. Mirrored by
# ../jspsych/strings.js.
NUMBER_WORDS = {
    "en": {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"},
    "de": {1: "ein", 2: "zwei", 3: "drei", 4: "vier", 5: "fünf"},
}
PAIR_REST = {
    "en": {3: "one more picture, before or after them",
           4: "two more pictures, before them, after them, or one on each side"},
    "de": {3: "ein weiteres Bild, davor oder danach",
           4: "zwei weitere Bilder, davor, danach oder je eines auf jeder Seite"},
}
SHAPE_WORDS = {
    "en": {"star": "star", "square": "square", "circle": "circle", "triangle": "triangle"},
    "de": {"star": "Stern", "square": "Quadrat", "circle": "Kreis", "triangle": "Dreieck"},
}


def step_terms(lang):
    """The route-length placeholders, read from config at call time so `--steps` is honoured."""
    n = cfg.N_STEPS
    words = NUMBER_WORDS[lang]
    names = [SHAPE_WORDS[lang][name] for name in cfg.PRACTICE_SHAPE_STEPS[:n]]
    # the last line of the instructions' summary names the practice in use (2026-10-01)
    line = "practice_line_real" if cfg.PRACTICE_STIMULI == "real" else "practice_line_shapes"
    return {"n_clips": words[n], "n_more_clips": words[n - 1], "shape_list": ", ".join(names),
            "n_journeys": words[3], "practice_line": STRINGS[lang][line],
            "pair_rest": PAIR_REST[lang][n],
            "intro_plan": STRINGS[lang]["intro_plan_real" if cfg.PRACTICE_STIMULI == "real"
                                        else "intro_plan_shapes"]}


def get(lang, key, **fmt):
    """Look up a string. The route-length placeholders are always available, so no call site can
       forget them; anything passed in `fmt` wins."""
    text = STRINGS[lang][key]
    values = step_terms(lang)
    values.update(fmt)
    return text.format(**values)


def probe_prompt(lang, direction):
    """The prompt for one probe, chosen ONLY by probe_direction. Never parses probe_question."""
    try:
        key = PROBE_PROMPT_KEYS[direction]
    except KeyError:
        raise KeyError(f"unknown probe_direction '{direction}'") from None
    return get(lang, key)
