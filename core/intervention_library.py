from typing import Dict, List, Optional, Any
import random

class InterventionLibrary:
    """
    A central registry for all available interventions (Intervention Cards).
    Organized by category: Physiology, Sensory, Cognitive.
    """

    def __init__(self):
        # Structure:
        # {
        #   "category_name": [
        #       {
        #           "id": "unique_id",
        #           "tier": 1, # 1=Gentle, 2=Moderate, 3=Urgent
        #           "description": "Short description",
        #           "sequence": [ # List of actions to execute
        #               {"action": "speak", "content": "Text to speak"},
        #               {"action": "wait", "duration": 2},
        #               {"action": "sound", "file": "path/to/sound.wav"}
        #           ]
        #       },
        #       ...
        #   ]
        # }
        self.library: Dict[str, List[Dict[str, Any]]] = {
            "physiology": [
                {
                    "id": "box_breathing",
                    "tier": 2,
                    "description": "4-4-4-4 Box Breathing exercise",
                    "sequence": [
                        {"action": "speak", "content": "Let's reset. Breathe in for 4."},
                        {"action": "wait", "duration": 4},
                        {"action": "speak", "content": "Hold for 4."},
                        {"action": "wait", "duration": 4},
                        {"action": "speak", "content": "Exhale for 4."},
                        {"action": "wait", "duration": 4},
                        {"action": "speak", "content": "Hold empty for 4."},
                        {"action": "wait", "duration": 4},
                        {"action": "speak", "content": "Good."}
                    ]
                },
                {
                    "id": "shoulder_drop",
                    "tier": 1,
                    "description": "Simple physical release",
                    "sequence": [
                        {"action": "speak", "content": "Check your shoulders. Are they up by your ears?"},
                        {"action": "wait", "duration": 2},
                        {"action": "speak", "content": "Drop them down. Take a deep breath."}
                    ]
                },
                {
                    "id": "eye_strain_release",
                    "tier": 1,
                    "description": "20-20-20 rule reminder",
                    "sequence": [
                        {"action": "speak", "content": "Your eyes need a break."},
                        {"action": "speak", "content": "Look at something 20 feet away for 20 seconds."},
                        {"action": "wait", "duration": 20},
                        {"action": "sound", "file": "assets/sounds/chime.wav"} # Placeholder path
                    ]
                }
            ],
            "sensory": [
                {
                    "id": "audio_grounding",
                    "tier": 2,
                    "description": "Listen for 3 distinct sounds",
                    "sequence": [
                        {"action": "speak", "content": "Close your eyes for a moment."},
                        {"action": "wait", "duration": 2},
                        {"action": "speak", "content": "Listen closely. Identify three distinct sounds you can hear right now."},
                        {"action": "wait", "duration": 10},
                        {"action": "speak", "content": "Okay."}
                    ]
                },
                {
                    "id": "visual_scan",
                    "tier": 1,
                    "description": "Find 5 blue objects",
                    "sequence": [
                        {"action": "speak", "content": "Quick game. Find 5 blue objects in the room. Go."},
                        {"action": "wait", "duration": 15},
                        {"action": "speak", "content": "Done."}
                    ]
                },
                {
                    "id": "cold_water",
                    "tier": 3,
                    "description": "Physiological reset via temperature",
                    "sequence": [
                        {"action": "speak", "content": "High arousal detected."},
                        {"action": "speak", "content": "Please go splash cold water on your face. It will help reset your nervous system."},
                        {"action": "visual_prompt", "content": "Splash cold water on face."}
                    ]
                }
            ],
            "cognitive": [
                {
                    "id": "context_switch",
                    "tier": 2,
                    "description": "Clear the mental buffer",
                    "sequence": [
                        {"action": "speak", "content": "You've been at this for a while."},
                        {"action": "speak", "content": "Stand up and walk away from the screen for just one minute."},
                        {"action": "wait", "duration": 60},
                        {"action": "sound", "file": "assets/sounds/chime.wav"}
                    ]
                },
                {
                    "id": "reality_check",
                    "tier": 1,
                    "description": "Simple check-in",
                    "sequence": [
                        {"action": "speak", "content": "Pause. Ask yourself: Is what I'm doing right now actually urgent?"},
                        {"action": "wait", "duration": 5}
                    ]
                },
                {
                    "id": "task_chunking",
                    "tier": 2,
                    "description": "Break down the problem",
                    "sequence": [
                        {"action": "speak", "content": "If you feel stuck, write down the next 3 smallest steps you can take."},
                        {"action": "visual_prompt", "content": "Write down 3 small steps."}
                    ]
                }
            ]
        }

    def get_intervention_by_id(self, intervention_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific intervention by its ID."""
        for category in self.library.values():
            for intervention in category:
                if intervention["id"] == intervention_id:
                    return intervention
        return None

    def get_interventions_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Retrieves all interventions in a specific category."""
        return self.library.get(category.lower(), [])

    def get_interventions_by_tier(self, tier: int) -> List[Dict[str, Any]]:
        """Retrieves all interventions of a specific tier across all categories."""
        result = []
        for category in self.library.values():
            for intervention in category:
                if intervention["tier"] == tier:
                    result.append(intervention)
        return result

    def get_random_intervention(self, category: Optional[str] = None, tier: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Selects a random intervention, optionally filtering by category and/or tier.
        """
        candidates = []

        # Filter by category first
        if category:
            source_list = self.library.get(category.lower(), [])
        else:
            source_list = [i for cat in self.library.values() for i in cat]

        # Filter by tier
        for intervention in source_list:
            if tier is not None:
                if intervention["tier"] == tier:
                    candidates.append(intervention)
            else:
                candidates.append(intervention)

        if not candidates:
            return None

        return random.choice(candidates)

if __name__ == "__main__":
    # Test the library
    lib = InterventionLibrary()

    print("--- Testing InterventionLibrary ---")

    # Test 1: Get by ID
    i1 = lib.get_intervention_by_id("box_breathing")
    print(f"Test 1 (Get by ID): Found {i1['id']}")
    assert i1["id"] == "box_breathing"
    assert len(i1["sequence"]) > 0

    # Test 2: Get by Category
    cat_list = lib.get_interventions_by_category("physiology")
    print(f"Test 2 (Get by Category): Found {len(cat_list)} in 'physiology'")
    assert len(cat_list) >= 3

    # Test 3: Get by Tier
    tier_list = lib.get_interventions_by_tier(3)
    print(f"Test 3 (Get by Tier 3): Found {len(tier_list)} tier 3 interventions")
    assert any(i["id"] == "cold_water" for i in tier_list)

    # Test 4: Random Selection
    rand_i = lib.get_random_intervention(category="cognitive", tier=1)
    print(f"Test 4 (Random Cognitive Tier 1): {rand_i['id'] if rand_i else 'None'}")
    assert rand_i["tier"] == 1

    print("InterventionLibrary tests passed.")
