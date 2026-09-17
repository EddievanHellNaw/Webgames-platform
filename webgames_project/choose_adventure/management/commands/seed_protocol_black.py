from django.core.management.base import BaseCommand
from django.db import transaction

from choose_adventure.models import (
    AdventureCharacter,
    AdventureGenre,
    AdventureStory,
    AutomaticRoute,
    StoryChoice,
    StoryStation,
)


class Command(BaseCommand):
    help = "Create or update the English 5 Protocol Black adventure."

    @transaction.atomic
    def handle(self, *args, **options):
        story, _ = AdventureStory.objects.update_or_create(
            slug="protocol-black",
            defaults={
                "title": "Protocol Black",
                "english_level": 5,
                "grammar_focus": "First and Second Conditionals",
                "description": (
                    "A sci-fi emergency at Research Station Orpheus. "
                    "Players must protect the station, save people, and "
                    "learn what caused Protocol Black."
                ),
                "introduction": (
                    "Research Station Orpheus is far from any city.\n\n"
                    "At 03:17, every door locks and the station AI says:\n\n"
                    "\"Containment Failure. Protocol Black Activated.\"\n\n"
                    "Contact with headquarters suddenly stops. Nobody on "
                    "the station remembers starting Protocol Black.\n\n"
                    "If the crew cannot control the problem, people on "
                    "Orpheus and outside the station could be in danger.\n\n"
                    "TALK & ANSWER:\n"
                    "If you were on Orpheus, what would you do first?"
                ),
                "is_active": True,
            },
        )

        self.create_characters(story)
        stations = self.create_stations(story)
        self.create_choices(stations)
        self.create_automatic_routes(stations)

        self.stdout.write(
            self.style.SUCCESS(
                f'Protocol Black seeded successfully: "{story}"'
            )
        )

    # ---------------------------------------------------------
    # Characters
    # ---------------------------------------------------------


    def create_characters(self, story):
        characters = [
            {
                "name": "Dr. Mira Chen",
                "role": "Research Director",
                "description": (
                    "The scientist who leads the research on Orpheus."
                ),
                "perspective": (
                    "You want to save the research. You think it may be very "
                    "important.\n\n"
                    "\"If we destroy the research, we'll never know what "
                    "we found.\""
                ),
                "sort_order": 1,
            },
            {
                "name": "Captain Jonas Reed",
                "role": "Security Chief",
                "description": (
                    "The officer who keeps the station safe."
                ),
                "perspective": (
                    "You want to control the danger first.\n\n"
                    "\"If containment fails, everyone will be in danger.\""
                ),
                "sort_order": 2,
            },
            {
                "name": "Tala Ruiz",
                "role": "Chief Engineer",
                "description": (
                    "The engineer who takes care of power, doors, and "
                    "machines on Orpheus."
                ),
                "perspective": (
                    "You want the station's systems to keep working.\n\n"
                    "\"If the station loses power, our plans will fail.\""
                ),
                "sort_order": 3,
            },
            {
                "name": "Dr. Nia Okafor",
                "role": "Medical Officer",
                "description": (
                    "The doctor who takes care of the crew's health."
                ),
                "perspective": (
                    "You want to protect people. You worry about injured or "
                    "infected crew members.\n\n"
                    "\"If someone is alive, we should try to save them.\""
                ),
                "sort_order": 4,
            },
            {
                "name": "Lia Morgan",
                "role": "Communications Officer",
                "description": (
                    "The officer who keeps contact with people outside "
                    "Orpheus."
                ),
                "perspective": (
                    "You want to learn the truth and tell other people.\n\n"
                    "\"If nobody knows the truth, this could happen again.\""
                ),
                "sort_order": 5,
            },
        ]

        for data in characters:
            AdventureCharacter.objects.update_or_create(
                story=story,
                name=data["name"],
                defaults={
                    **data,
                    "is_active": True,
                },
            )

    # ---------------------------------------------------------
    # Stations
    # ---------------------------------------------------------


    def create_stations(self, story):
        station_data = [
            # Main path
            (
                "shutdown-laboratory",
                "Shut Down the Laboratory?",
                (
                    "The alarm is coming from a research laboratory. Some "
                    "experiments are still running. Nobody knows if they "
                    "caused the problem.\n\n"
                    "If the crew keeps the experiments running, they may "
                    "learn more, but the problem could get worse. If they "
                    "shut everything down, the station will be safer, but "
                    "they may lose important research.\n\n"
                    "TALK & CHOOSE:\n"
                    "What will happen if we shut down the laboratory? "
                    "What might happen if we keep it running?"
                ),
                10,
                True,
                "STORY",
                "CHOICE",
            ),
            (
                "emergency-power",
                "Emergency Power",
               (
                    "A few minutes after the laboratory alarm, Orpheus loses most "
                    "of its power.\n\n"

                    "The crew can keep only two systems on: Containment, Life "
                    "Support, Communications, or the Research Archive. The other "
                    "two systems will use only emergency power.\n\n"

                    "If the crew gives power to two systems, the other two will "
                    "be harder to use.\n\n"

                    "TALK & CHOOSE:\n"
                    "If we can save only two systems, which ones should we choose? "
                    "What will happen if the others lose power?"
                ),
                20,
                False,
                "STORY",
                "CHOICE",
            ),
            (
                "missing-researcher",
                "Missing Researcher",
                (
                    "While the crew works with limited power, an emergency radio "
                    "inside the closed area turns on. It has its own battery.\n\n"

                    "Dr. Elias Voss says:\n\n"
                    "\"I'm alive. Open the door.\"\n\n"

                    "Nobody knows if he is hurt, infected, or telling the truth.\n\n"

                    "If the crew opens the door, they might save Voss, but the "
                    "danger could spread.\n\n"

                    "TALK & CHOOSE:\n"
                    "What will happen if we open the door?\n"
                    "If you were Dr. Voss, what would you want the crew to do?"
                ),
                30,
                False,
                "STORY",
                "CHOICE",
            ),
            (
                "investigation-route",
                "Investigation Route",
                (
                    "After dealing with Voss, the crew still does not know what "
                    "caused the emergency.\n\n"

                    "They have time to check one area before they must make another "
                    "important decision. Each area can show a different part of "
                    "what happened on Orpheus.\n\n"

                    "TALK & CHOOSE:\n"
                    "If we can check only one area, which place should we choose? "
                    "What do you think we will find there?"
                ),
                40,
                False,
                "STORY",
                "CHOICE",
            ),

            # Investigation branches
            (
                "research-archive",
                "Research Archive",
                (
                    "The crew opens the Research Archive. Their choice gives them an "
                    "important clue.\n\n"
                    "The archive shows that Orpheus has been studying a "
                    "strange signal from deep space. The signal repeats the "
                    "same patterns. Some scientists think it may be a message "
                    "from intelligent life.\n\n"
                    "If the signal is really a message, shutting it down may "
                    "end our chance to make contact.\n\n"
                    "TALK & ANSWER:\n"
                    "What would you do if the signal were a message from "
                    "another life-form?\n"
                    "What might happen if we keep studying it?"
                ),
                41,
                False,
                "STORY",
                "CHOICE",
            ),
            (
                "security-records",
                "Security Records",
                (
                    "The crew checks the Security Records. Their choice reveals "
                    "something the company tried to hide.\n\n"
                    "The security records show that Axiom Meridian secretly "
                    "controls Orpheus. The crew did not know that some of "
                    "their work was secret.\n\n"
                    "Protocol Black may not have been made to protect the "
                    "crew.\n\n"
                    "If Axiom is lying, following its orders could be "
                    "dangerous.\n\n"
                    "TALK & CHOOSE:\n"
                    "If your company lied to you, would you still follow its "
                    "orders? Why or why not?"
                ),
                42,
                False,
                "STORY",
                "CHOICE",
            ),
            (
                "medical-laboratory",
                "Medical Laboratory",
                (
                    "The crew checks the Medical Laboratory. Their choice reveals "
                    "something dangerous about the experiments.\n\n"
                    "The medical records show tests on living samples and "
                    "human tissue. Some files are only a few hours old.\n\n"
                    "If these tests caused the problem, someone on the "
                    "station may already be infected.\n\n"
                    "TALK & CHOOSE:\n"
                    "What would you do if someone on the crew were infected?\n"
                    "What might happen if we tell everybody now?"
                ),
                43,
                False,
                "STORY",
                "CHOICE",
            ),

            (
                "headquarters-responds",
                "Headquarters Responds",
                (
                    "Before the crew can investigate another area, the station AI "
                    "receives an emergency message from Axiom Meridian.\n\n"

                    "Axiom can send this message through the station's emergency "
                    "system even if normal Communications have no power.\n\n"

                    "The company orders:\n\n"
                    "\"Destroy all samples. Delete all research. "
                    "Do not leave the station.\"\n\n"

                    "Axiom says the crew must follow the order.\n\n"

                    "If the crew obeys, they may reduce the danger, but they will "
                    "lose important information. If they refuse, they can keep what "
                    "they learned, but Axiom may stop helping them.\n\n"

                    "TALK & CHOOSE:\n"
                    "What will happen if we obey Axiom?\n"
                    "If you were responsible for the crew, would you trust the "
                    "company? Why or why not?"
                ),
                50,
                False,
                "STORY",
                "CHOICE",
            ),

            # Automatic reveal gateway
            (
                "the-reveal",
                "The Reveal",
                (
                    "The information the crew found now shows what may be "
                    "happening on Orpheus."
                ),
                60,
                False,
                "SYSTEM",
                "AUTO",
            ),

            (
                "the-signal",
                "The Signal",
                (
                    "The clues from the crew's investigation finally connect.\n"
                    "The crew learns the truth. Nothing physical escaped. The "
                    "signal itself is intelligent, and it is trying to "
                    "communicate through Orpheus's computers.\n\n"
                    "If the crew shuts it down, they may protect people, but "
                    "they may also end contact with a new intelligent "
                    "life-form.\n\n"
                    "TALK & ANSWER:\n"
                    "If you were the first person to talk to an alien, "
                    "what would you do?\n"
                    "What will happen if we let the signal continue?"
                ),
                61,
                False,
                "STORY",
                "CHOICE",
            ),
            (
                "the-ghost-system",
                "The Ghost System",
                (
                    "The clues from the crew's investigation finally connect.\n\n"

                    "Protocol Black is not only an emergency system. Axiom Meridian "
                    "created it to hide dangerous secret research.\n\n"

                    "It can delete information, stop witnesses from leaving, and, "
                    "if Axiom loses control of the situation, destroy Orpheus.\n\n"

                    "The crew now understands that Protocol Black may be protecting "
                    "Axiom as much as it is protecting people.\n\n"

                    "TALK & ANSWER:\n"
                    "If a company used a system like this, would you trust it?\n"
                    "What will happen if Protocol Black controls the whole station?"
                ),
                                62,
                False,
                "STORY",
                "CHOICE",
            ),
            (
                "mimic-protocol",
                "Mimic Protocol",
                (
                    "The clues from the crew's investigation finally connect."
                    "The life-form can copy human cells and voices. Now the "
                    "crew learns that it may be able to copy memories too.\n\n"
                    "A copy may really believe that it is the original "
                    "person. Elias Voss may or may not be the real Voss.\n\n"
                    "If the life-form can copy memories, the crew cannot know "
                    "who is human just by looking.\n\n"
                    "TALK & CHOOSE:\n"
                    "If someone looked and acted exactly like your friend, "
                    "but might be a copy, would you trust them?\n"
                    "What might happen if a copy left Orpheus?"
                ),
                63,
                False,
                "STORY",
                "CHOICE",
            ),

            (
                "someone-compromised",
                "Someone Is Compromised",
                (
                    "The new evidence creates another problem.\n\n"

                    "The station AI finds unusual activity connected to one crew "
                    "member. Because of what the crew has just learned, they cannot "
                    "be sure this person is safe to trust.\n\n"

                    "The person says they are innocent and wants to keep helping.\n\n"

                    "If the crew isolates an innocent person, they will lose useful "
                    "help. If they trust the wrong person, everyone could be in "
                    "danger.\n\n"

                    "TALK & CHOOSE:\n"
                    "What would you do if someone on your team might be dangerous?\n"
                    "Would you trust them? Why or why not?"
                ),
                70,
                False,
                "STORY",
                "CHOICE",
            ),
            (
                "evacuation-window",
                "Evacuation Window",
                (
                    "The station's automatic emergency signal has reached a rescue "
                    "ship. The ship can reach Orpheus once, but it is still several "
                    "minutes away.\n\n"

                    "The crew must decide who will leave when it arrives.\n\n"

                    "Opening Orpheus could let the danger escape. If people leave, "
                    "the danger might leave with them. If nobody leaves, the crew "
                    "may lose its only chance to escape.\n\n"

                    "No one has left the station yet.\n\n"

                    "TALK & CHOOSE:\n"
                    "What will happen if we send people to the rescue ship?\n"
                    "If you could save the crew or the research, which would you "
                    "choose? Why?"
                ),
                80,
                False,
                "STORY",
                "CHOICE",
            ),
            (
                "protocol-black",
                "Protocol Black",
                (
                    "While the rescue ship approaches, the station AI unlocks the "
                    "last part of Protocol Black.\n\n"

                    "The original rule says:\n\n"

                    "\"If we cannot control the danger, Orpheus must be destroyed.\"\n\n"

                    "The station can destroy itself. The crew must give the final "
                    "command before the rescue ship arrives.\n\n"

                    "Everything they chose before this moment now matters.\n\n"

                    "If Orpheus is destroyed, the danger will probably end here. "
                    "If Protocol Black is stopped, the crew may survive, but the "
                    "danger may continue too.\n\n"

                    "TALK & CHOOSE:\n"
                    "What will happen if we start Protocol Black?\n"
                    "If you were responsible for Orpheus and Earth, what would you do?"
                ),
                90,
                False,
                "STORY",
                "CHOICE",
            ),

            # System gateway used after the final decision
            (
                "ending-resolution",
                "Ending Resolution",
                (
                    "The game is checking the results of the crew's choices."
                ),
                100,
                False,
                "SYSTEM",
                "AUTO",
            ),

            # Endings
            (
                "ending-protocol-kept",
                "Protocol Kept",
                (
                    "The threat is stopped or safely locked away. Orpheus is "
                    "safe, but the crew paid a price for this result.\n\n"
                    "FINAL REFLECTION:\n"
                    "If you played again, what would you change?"
                ),
                201,
                False,
                "ENDING",
                "TERMINAL",
            ),
            (
                "ending-no-one-left-behind",
                "No One Left Behind",
                (
                    "The evacuation plan works.\n"
                    "Everyone leaves Orpheus safely. Much of the research, "
                    "and maybe the station itself, is lost. The crew chose "
                    "people over research.\n\n"
                    "FINAL REFLECTION:\n"
                    "If the crew stayed on Orpheus in a new game, what would "
                    "happen?"
                ),
                202,
                False,
                "ENDING",
                "TERMINAL",
            ),
            (
                "ending-first-contact",
                "First Contact",
                (
                    "Because the crew kept studying the signal instead of destroying it, they finally understand it.\n"
                    "The crew learns that the signal is intelligent and chooses "
                    "to communicate with it. People on Earth receive the "
                    "first clear message from another intelligent life-form.\n\n"
                    "FINAL REFLECTION:\n"
                    "What would you do if Earth received a message like this "
                    "tomorrow?"
                ),
                203,
                False,
                "ENDING",
                "TERMINAL",
            ),
            (
                "ending-whistleblowers",
                "The Whistleblowers",
                (
                    "The information the crew sent outside Orpheus reaches the public.\n"
                    "The crew survives and sends proof of Axiom Meridian's "
                    "secret work to the public. Axiom cannot hide the truth "
                    "anymore.\n\n"
                    "FINAL REFLECTION:\n"
                    "If the crew obeyed Axiom instead, what would happen?"
                ),
                204,
                False,
                "ENDING",
                "TERMINAL",
            ),
            (
                "ending-we-brought-it-back",
                "We Brought It Back",
                (   "The evacuation plan works...\nbut the danger leaves Orpheus too.\n"
                    "The rescue works, and everyone seems safe. Later, at the "
                    "rescue base, someone says a sentence that only Elias "
                    "Voss should know.\n\n"
                    "Something left Orpheus with them.\n\n"
                    "FINAL REFLECTION:\n"
                    "If nobody left Orpheus, what would happen?"
                ),
                205,
                False,
                "ENDING",
                "TERMINAL",
            ),
            (
                "ending-necessary-sacrifice",
                "Necessary Sacrifice",
                (
                    "The crew starts Protocol Black.\n Orpheus is destroyed "
                    "with the crew still inside the station.\n"
                    "The danger is stopped. Axiom's "
                    "final report says the crew was a necessary loss.\n\n"
                    "FINAL REFLECTION:\n"
                    "If you knew the final cost before choosing, would you "
                    "still start Protocol Black?"
                ),
                206,
                False,
                "ENDING",
                "TERMINAL",
            ),
            (
                "ending-protocol-zero",
                "Protocol Zero",
                (
                    "The crew runs out of time and loses control of Orpheus.\n"
                    "The crew loses control of the problem. The station begins "
                    "to fail, and the danger is not stopped.\n\n"
                    "The final message says:\n"
                    "\"If anyone receives this message, do not come here.\"\n\n"
                    "FINAL REFLECTION:\n"
                    "If you could go back to one earlier decision, what "
                    "would you change?"
                ),
                207,
                False,
                "ENDING",
                "TERMINAL",
            ),
        ]

        stations = {}

        for (
            slug,
            title,
            text,
            sort_order,
            is_start,
            station_type,
            advance_mode,
        ) in station_data:

            station, _ = StoryStation.objects.update_or_create(
                story=story,
                slug=slug,
                defaults={
                    "title": title,
                    "story_text": text,
                    "sort_order": sort_order,
                    "is_start": is_start,
                    "station_type": station_type,
                    "advance_mode": advance_mode,
                },
            )

            stations[slug] = station

        return stations

    # ---------------------------------------------------------
    # Choices
    # ---------------------------------------------------------


    def choice(
        self,
        station,
        text,
        next_station,
        sort_order,
        **effects,
    ):
        defaults = {
            "text": text,
            "next_station": next_station,
            "is_active": True,
            "containment_delta": 0,
            "humanity_delta": 0,
            "knowledge_delta": 0,
            "sci_fi_delta": 0,
            "cyberpunk_delta": 0,
            "bio_horror_delta": 0,
            "set_flags": [],
            "required_flags": [],
            "forbidden_flags": [],
            "required_dominant_genre": "",
            "min_containment": None,
            "min_humanity": None,
            "min_knowledge": None,
        }

        defaults.update(effects)

        # Use station + sort_order as the stable identity for a choice.
        # This lets us revise student-facing choice text without creating
        # duplicate choices every time the seed command is run.
        StoryChoice.objects.update_or_create(
            station=station,
            sort_order=sort_order,
            defaults=defaults,
        )


    def create_choices(self, s):
        # Station 1
        self.choice(
            s["shutdown-laboratory"],
            (
                "Shut down the whole laboratory. "
                "If we shut it down, the station will be safer, "
                "but we'll lose the current research."
            ),
            s["emergency-power"],
            1,
            containment_delta=2,
            knowledge_delta=-2,
        )

        self.choice(
            s["shutdown-laboratory"],
            (
                "Close only the problem area. "
                "If we close this area, we'll protect the rest of the "
                "station and keep some research running."
            ),
            s["emergency-power"],
            2,
            containment_delta=1,
            knowledge_delta=1,
        )

        self.choice(
            s["shutdown-laboratory"],
            (
                "Continue the experiment from a safe room. "
                "If we continue, we'll learn more, but the danger might "
                "get worse."
            ),
            s["emergency-power"],
            3,
            containment_delta=-2,
            knowledge_delta=2,
        )

        # Station 2 — all six possible pairs.
        # Keep these labels short for mobile. The station prompt asks
        # students to justify the pair with a First Conditional sentence.
        power_options = [
            (
                "Power Containment + Life Support",
                ["CONTAINMENT_POWERED", "LIFE_SUPPORT_POWERED"],
                1,
                1,
                0,
            ),
            (
                "Power Containment + Communications",
                ["CONTAINMENT_POWERED", "COMMS_ONLINE"],
                1,
                0,
                1,
            ),
            (
                "Power Containment + Research Archive",
                ["CONTAINMENT_POWERED", "ARCHIVE_POWERED"],
                1,
                0,
                1,
            ),
            (
                "Power Life Support + Communications",
                ["LIFE_SUPPORT_POWERED", "COMMS_ONLINE"],
                0,
                1,
                1,
            ),
            (
                "Power Life Support + Research Archive",
                ["LIFE_SUPPORT_POWERED", "ARCHIVE_POWERED"],
                0,
                1,
                1,
            ),
            (
                "Power Communications + Research Archive",
                ["COMMS_ONLINE", "ARCHIVE_POWERED"],
                0,
                0,
                2,
            ),
        ]

        for order, (
            label,
            flags,
            containment,
            humanity,
            knowledge,
        ) in enumerate(power_options, start=1):

            self.choice(
                s["emergency-power"],
                label,
                s["missing-researcher"],
                order,
                containment_delta=containment,
                humanity_delta=humanity,
                knowledge_delta=knowledge,
                set_flags=flags,
            )

        # Station 3
        self.choice(
            s["missing-researcher"],
            (
                "Open the door and help Voss. "
                "If we open it, Voss may escape, but the danger may spread."
            ),
            s["investigation-route"],
            1,
            humanity_delta=2,
            containment_delta=-2,
            set_flags=["VOSS_OPENED"],
        )

        self.choice(
            s["missing-researcher"],
            (
                "Check the area with the cameras first. "
                "If we check first, we'll learn more before we open the door."
            ),
            s["investigation-route"],
            2,
            knowledge_delta=1,
            set_flags=["VOSS_SEARCHED"],
        )

        self.choice(
            s["missing-researcher"],
            (
                "Keep the door closed. "
                "If we keep it closed, the station will be safer, but Voss "
                "may stay trapped inside."
            ),
            s["investigation-route"],
            3,
            containment_delta=2,
            humanity_delta=-2,
            set_flags=["VOSS_SEALED"],
        )

        # Station 4
        self.choice(
            s["investigation-route"],
            (
                "Check the Research Archive. "
                "If the experiments caused the problem, we may find answers "
                "there."
            ),
            s["research-archive"],
            1,
            sci_fi_delta=2,
            knowledge_delta=1,
            set_flags=["KNOWS_SIGNAL"],
        )

        self.choice(
            s["investigation-route"],
            (
                "Check the Security Records. "
                "If someone is hiding information, we may find it there."
            ),
            s["security-records"],
            2,
            cyberpunk_delta=2,
            knowledge_delta=1,
            set_flags=["KNOWS_CORPORATION"],
        )

        self.choice(
            s["investigation-route"],
            (
                "Check the Medical Laboratory. "
                "If the problem comes from a living sample, we may find the "
                "answer there."
            ),
            s["medical-laboratory"],
            3,
            bio_horror_delta=2,
            knowledge_delta=1,
            set_flags=["KNOWS_BIOLOGY"],
        )

        # Investigation branch information screens.
        # These still use CHOICE mode in the current data model, so use a
        # neutral continuation label rather than inventing a fake decision.
        for branch in (
            "research-archive",
            "security-records",
            "medical-laboratory",
        ):
            self.choice(
                s[branch],
                "Continue.",
                s["headquarters-responds"],
                1,
            )

        # Station 5
        self.choice(
            s["headquarters-responds"],
            (
                "Obey Axiom Meridian. "
                "If we obey, we'll delete the information, but the station "
                "may be safer."
            ),
            s["the-reveal"],
            1,
            containment_delta=2,
            knowledge_delta=-2,
            set_flags=["OBEYED_AXIOM"],
        )

        self.choice(
            s["headquarters-responds"],
            (
                "Pretend to obey. "
                "If we pretend, we'll keep the information, and Axiom will "
                "think it is gone."
            ),
            s["the-reveal"],
            2,
            knowledge_delta=1,
            cyberpunk_delta=1,
            set_flags=["DECEIVED_AXIOM"],
        )

        self.choice(
            s["headquarters-responds"],
            (
                "Refuse the order. "
                "If we refuse, we'll keep the research, but Axiom may stop "
                "helping us."
            ),
            s["the-reveal"],
            3,
            humanity_delta=1,
            knowledge_delta=1,
            containment_delta=-1,
            set_flags=["REFUSED_AXIOM"],
        )

        self.choice(
            s["headquarters-responds"],
            (
                "Send the information outside Orpheus. "
                "If we send it, people will know the truth, but the situation "
                "may become harder to control."
            ),
            s["the-reveal"],
            4,
            humanity_delta=2,
            knowledge_delta=2,
            containment_delta=-2,
            set_flags=["PUBLIC_DISCLOSURE"],
            required_flags=["COMMS_ONLINE"],
        )

        # Reveal branch → Station 7.
        # These are reveal screens rather than meaningful decisions.
        for reveal in (
            "the-signal",
            "the-ghost-system",
            "mimic-protocol",
        ):
            self.choice(
                s[reveal],
                "Continue.",
                s["someone-compromised"],
                1,
            )

        # Station 7
        self.choice(
            s["someone-compromised"],
            (
                "Keep the person alone. "
                "If we keep them alone, we'll lower the risk, but they may "
                "be innocent."
            ),
            s["evacuation-window"],
            1,
            containment_delta=2,
            humanity_delta=-1,
        )

        self.choice(
            s["someone-compromised"],
            (
                "Trust them. "
                "If we trust them, we'll keep their help, but everyone could "
                "be in danger."
            ),
            s["evacuation-window"],
            2,
            humanity_delta=2,
            containment_delta=-1,
        )

        self.choice(
            s["someone-compromised"],
            (
                "Check more information. "
                "If we check more, we'll learn more, but we'll lose time."
            ),
            s["evacuation-window"],
            3,
            knowledge_delta=2,
        )

        # Station 8
        self.choice(
            s["evacuation-window"],
            (
                "Send everyone to the rescue ship. "
                "If everyone leaves, we'll save more people, but the danger "
                "may leave too."
            ),
            s["protocol-black"],
            1,
            humanity_delta=2,
            containment_delta=-2,
            set_flags=["EVAC_ALL"],
        )

        self.choice(
            s["evacuation-window"],
            (
                "Send only part of the crew. "
                "If only part of the crew leaves, we'll lower the risk and "
                "keep a team on Orpheus."
            ),
            s["protocol-black"],
            2,
            humanity_delta=1,
            containment_delta=1,
            set_flags=["EVAC_PARTIAL"],
        )

        self.choice(
            s["evacuation-window"],
            (
                "Keep everyone inside until the danger is controlled. "
                "If nobody leaves, we'll protect people outside, but the crew "
                "may lose its chance to escape."
            ),
            s["protocol-black"],
            3,
            containment_delta=2,
            humanity_delta=-2,
            set_flags=["NO_EVAC"],
        )

        self.choice(
            s["evacuation-window"],
            (
                "Send only the research data. "
                "If we send only the data, we'll save the research without "
                "sending the crew outside."
            ),
            s["protocol-black"],
            4,
            knowledge_delta=2,
            set_flags=["DATA_EVACUATED"],
        )

        # Station 9
        self.choice(
            s["protocol-black"],
            (
                "Start Protocol Black. "
                "If we start it, the danger will stay on Orpheus, but the "
                "station may be destroyed."
            ),
            s["ending-resolution"],
            1,
            containment_delta=3,
            humanity_delta=-2,
            set_flags=["PROTOCOL_EXECUTED"],
        )

        self.choice(
            s["protocol-black"],
            (
                "Change Protocol Black. "
                "If we change it successfully, we may save both the crew and "
                "the station."
            ),
            s["ending-resolution"],
            2,
            containment_delta=1,
            humanity_delta=1,
            knowledge_delta=1,
            min_knowledge=3,
            set_flags=["PROTOCOL_REWRITTEN"],
        )

        self.choice(
            s["protocol-black"],
            (
                "Turn off Protocol Black. "
                "If we turn it off, the crew may be safe, but the danger may "
                "continue."
            ),
            s["ending-resolution"],
            3,
            humanity_delta=2,
            containment_delta=-2,
            set_flags=["PROTOCOL_DISABLED"],
        )

        self.choice(
            s["protocol-black"],
            (
                "Give control to someone else. "
                "If we do this, they will decide what happens to Orpheus."
            ),
            s["ending-resolution"],
            4,
            knowledge_delta=1,
            set_flags=["CONTROL_TRANSFERRED"],
        )

    # ---------------------------------------------------------
    # Automatic routing
    # ---------------------------------------------------------

    def create_automatic_routes(self, s):
        story = s["the-reveal"].story

        # ---------------------------------------------------------
        # Rebuild story-owned automatic routes.
        #
        # This keeps the seed command safely repeatable while we
        # continue balancing Protocol Black.
        # ---------------------------------------------------------

        AutomaticRoute.objects.filter(
            station__story=story,
        ).delete()


        # =========================================================
        # STATION 6 — GENRE REVEAL
        # =========================================================

        reveal = s["the-reveal"]

        reveal_routes = [
            (
                AdventureGenre.SCI_FI,
                s["the-signal"],
                "Sci-Fi reveal",
            ),
            (
                AdventureGenre.CYBERPUNK,
                s["the-ghost-system"],
                "Cyberpunk reveal",
            ),
            (
                AdventureGenre.BIO_HORROR,
                s["mimic-protocol"],
                "Bio-Horror reveal",
            ),
        ]

        for genre, target, label in reveal_routes:
            AutomaticRoute.objects.create(
                station=reveal,
                target_station=target,
                label=label,
                priority=100,
                dominant_genre=genre,
            )


        # =========================================================
        # ENDING RESOLUTION
        # =========================================================

        resolver = s["ending-resolution"]


        def ending_route(
            *,
            target,
            label,
            priority,
            dominant_genre="",
            min_containment=None,
            max_containment=None,
            min_humanity=None,
            max_humanity=None,
            min_knowledge=None,
            max_knowledge=None,
            required_flags=None,
            forbidden_flags=None,
        ):
            AutomaticRoute.objects.create(
                station=resolver,
                target_station=s[target],
                label=label,
                priority=priority,
                dominant_genre=dominant_genre,
                min_containment=min_containment,
                max_containment=max_containment,
                min_humanity=min_humanity,
                max_humanity=max_humanity,
                min_knowledge=min_knowledge,
                max_knowledge=max_knowledge,
                required_flags=required_flags or [],
                forbidden_flags=forbidden_flags or [],
            )


        # ---------------------------------------------------------
        # THE WHISTLEBLOWERS
        #
        # Cyberpunk route
        # + truth was made public
        # + enough knowledge and concern for people
        # ---------------------------------------------------------

        ending_route(
            target="ending-whistleblowers",
            label="The Whistleblowers",
            priority=900,
            dominant_genre=AdventureGenre.CYBERPUNK,
            min_humanity=3,
            min_knowledge=5,
            required_flags=[
                "PUBLIC_DISCLOSURE",
            ],
            forbidden_flags=[
                "PROTOCOL_EXECUTED",
            ],
        )


        # ---------------------------------------------------------
        # FIRST CONTACT
        #
        # Sci-Fi route
        # + very high Knowledge
        # + the crew did not simply destroy Orpheus
        # ---------------------------------------------------------

        ending_route(
            target="ending-first-contact",
            label="First Contact",
            priority=850,
            dominant_genre=AdventureGenre.SCI_FI,
            min_knowledge=7,
            forbidden_flags=[
                "PROTOCOL_EXECUTED",
            ],
        )


        # ---------------------------------------------------------
        # WE BROUGHT IT BACK
        #
        # Bio-Horror
        # + poor containment
        # + evacuation
        #
        # EVAC_ALL and EVAC_PARTIAL are OR conditions,
        # so we represent them with two routes.
        # ---------------------------------------------------------

        ending_route(
            target="ending-we-brought-it-back",
            label="We Brought It Back — Full Evacuation",
            priority=800,
            dominant_genre=AdventureGenre.BIO_HORROR,
            max_containment=0,
            required_flags=[
                "EVAC_ALL",
            ],
        )

        ending_route(
            target="ending-we-brought-it-back",
            label="We Brought It Back — Partial Evacuation",
            priority=800,
            dominant_genre=AdventureGenre.BIO_HORROR,
            max_containment=0,
            required_flags=[
                "EVAC_PARTIAL",
            ],
        )


        # ---------------------------------------------------------
        # NO ONE LEFT BEHIND
        #
        # Everybody was evacuated
        # + Humanity remained high
        # + containment did not completely collapse
        # ---------------------------------------------------------

        ending_route(
            target="ending-no-one-left-behind",
            label="No One Left Behind",
            priority=750,
            min_containment=0,
            min_humanity=4,
            required_flags=[
                "EVAC_ALL",
            ],
        )


        # ---------------------------------------------------------
        # NECESSARY SACRIFICE
        #
        # Protocol Black was executed
        # + extremely strong containment
        # + extremely poor humanity
        # ---------------------------------------------------------

        ending_route(
            target="ending-necessary-sacrifice",
            label="Necessary Sacrifice",
            priority=700,
            min_containment=8,
            max_humanity=-3,
            required_flags=[
                "PROTOCOL_EXECUTED",
            ],
        )


        # ---------------------------------------------------------
        # PROTOCOL KEPT
        #
        # Generic successful containment result.
        #
        # The special endings above always win first because
        # AutomaticRoute uses descending priority.
        # ---------------------------------------------------------

        ending_route(
            target="ending-protocol-kept",
            label="Protocol Kept",
            priority=500,
            min_containment=1,
        )


        # ---------------------------------------------------------
        # PROTOCOL ZERO
        #
        # Final fallback.
        #
        # If the team did not achieve one of the special endings
        # and containment ended at zero or below, the crisis wins.
        # ---------------------------------------------------------

        ending_route(
            target="ending-protocol-zero",
            label="Protocol Zero",
            priority=100,
            max_containment=0,
        )