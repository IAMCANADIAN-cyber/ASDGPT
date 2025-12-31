from typing import Dict, List, Optional, Any

class InterventionLibrary:
    """
    Registry of interventions available to the system.
    Each intervention is defined by an ID, category, tier, and a sequence of actions.
    """

    def __init__(self):
        self.interventions: Dict[str, Dict[str, Any]] = {
            # --- Physiology ---
            "phys_box_breathing": {
                "id": "phys_box_breathing",
                "category": "physiology",
                "tier": 2,
                "description": "4-4-4-4 Box Breathing to lower arousal.",
                "sequence": [
                    {"action": "speak", "text": "Let's reset. Box breathing."},
                    {"action": "wait", "duration": 1},
                    {"action": "speak", "text": "Breathe in... 2... 3... 4"},
                    {"action": "wait", "duration": 4},
                    {"action": "speak", "text": "Hold... 2... 3... 4"},
                    {"action": "wait", "duration": 4},
                    {"action": "speak", "text": "Exhale... 2... 3... 4"},
                    {"action": "wait", "duration": 4},
                    {"action": "speak", "text": "Hold empty... 2... 3... 4"},
                    {"action": "wait", "duration": 4},
                    {"action": "speak", "text": "Resume normal breathing."}
                ]
            },
            "phys_posture_reset": {
                "id": "phys_posture_reset",
                "category": "physiology",
                "tier": 1,
                "description": "Quick posture check.",
                "sequence": [
                    {"action": "speak", "text": "Posture check. Shoulders down, chin back."},
                    {"action": "wait", "duration": 5},
                    {"action": "speak", "text": "Better."}
                ]
            },
            "phys_cold_water": {
                "id": "phys_cold_water",
                "category": "physiology",
                "tier": 2,
                "description": "Temperature reset.",
                "sequence": [
                    {"action": "speak", "text": "High arousal detected. Splash cold water on your face or grab an ice pack."},
                    {"action": "wait", "duration": 15}, # Give them time to get up
                ]
            },

            # --- Sensory ---
            "sens_dim_lights": {
                "id": "sens_dim_lights",
                "category": "sensory",
                "tier": 1,
                "description": "Reduce visual input.",
                "sequence": [
                    {"action": "speak", "text": "Sensory load is high. Try dimming the lights or closing your eyes for a moment."}
                ]
            },
            "sens_headphones_on": {
                "id": "sens_headphones_on",
                "category": "sensory",
                "tier": 2,
                "description": "Reduce auditory input.",
                "sequence": [
                    {"action": "speak", "text": "Put on noise-cancelling headphones or play brown noise."},
                ]
            },
            "sens_quiet_mode": {
                "id": "sens_quiet_mode",
                "category": "sensory",
                "tier": 2,
                "description": "System entering quiet mode.",
                "sequence": [
                    {"action": "speak", "text": "Switching to quiet mode. I will minimize interruptions."},
                    # LogicEngine would handle the actual mode switch if integrated,
                    # but this is the intervention content.
                ]
            },

            # --- Cognitive ---
            "cog_bookmark": {
                "id": "cog_bookmark",
                "category": "cognitive",
                "tier": 1,
                "description": "Save current state to prevent loss aversion.",
                "sequence": [
                    {"action": "speak", "text": "Write down the one next thing you need to do, then stand up."},
                ]
            },
            "cog_task_slice": {
                "id": "cog_task_slice",
                "category": "cognitive",
                "tier": 1,
                "description": "Break down a stuck task.",
                "sequence": [
                    {"action": "speak", "text": "You seem stuck. What is the smallest physical action you can do next?"},
                ]
            },
            "cog_next_action": {
                "id": "cog_next_action",
                "category": "cognitive",
                "tier": 1,
                "description": "Focus on immediate step.",
                "sequence": [
                    {"action": "speak", "text": "Forget the big picture. Just do the very next step."}
                ]
            }
        }

    def get_intervention(self, intervention_id: str) -> Optional[Dict[str, Any]]:
        return self.interventions.get(intervention_id)

    def get_interventions_by_category(self, category: str) -> List[Dict[str, Any]]:
        return [i for i in self.interventions.values() if i["category"] == category]

    def get_all_interventions(self) -> List[Dict[str, Any]]:
        return list(self.interventions.values())

if __name__ == "__main__":
    lib = InterventionLibrary()
    print(f"Total interventions: {len(lib.get_all_interventions())}")
    box_breath = lib.get_intervention("phys_box_breathing")
    print(f"Box Breathing Steps: {len(box_breath['sequence'])}")
    assert box_breath is not None
    assert len(box_breath["sequence"]) > 0
