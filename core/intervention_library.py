from typing import Dict, List, Optional, Any
import random

class InterventionLibrary:
    """
    A central registry for all available interventions (Intervention Cards).
    Organized by category: Physiology, Sensory, Cognitive, Creative, Recovery, Social.
    """

    def __init__(self):
        # Structure:
        # {
        #   "category_name": [
        #       {
        #           "id": "unique_id",
        #           "tier": 1, # 1=Gentle/Nudge, 2=Moderate/Choice, 3=Urgent/Escalate
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
                },
                {
                    "id": "posture_water_reset",
                    "tier": 1,
                    "description": "Quick posture check and hydration reminder (Flow state protection)",
                    "sequence": [
                        {"action": "speak", "content": "You're in flow. Let's protect it. 30 second reset."},
                        {"action": "speak", "content": "Sit up straight. Take a sip of water."},
                        {"action": "wait", "duration": 5},
                        {"action": "speak", "content": "Back to it."}
                    ]
                },
                {
                    "id": "stand_reset",
                    "tier": 2,
                    "description": "Stand up to break hyperfocus or drowsiness",
                    "sequence": [
                        {"action": "speak", "content": "Stand up. Right now."},
                        {"action": "wait", "duration": 2},
                        {"action": "speak", "content": "Stretch your arms up. Take a deep breath."},
                        {"action": "wait", "duration": 5},
                        {"action": "speak", "content": "Good."}
                    ]
                },
                {
                   "id": "arousal_redirect",
                   "tier": 3,
                   "description": "Direct intervention to resolve urge efficiently and return to baseline",
                   "sequence": [
                       {"action": "speak", "content": "Hey Austin, I think you're pretty turned on right now and it is causing you to waste time scrolling. What I want you to do is lay down in bed, put away your phone, and I'll walk you through a guided mindful masturbation session and I will watch and listen to you while we do it."}
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
                },
                {
                    "id": "reduce_input",
                    "tier": 2,
                    "description": "Overload management: reduce sensory input",
                    "sequence": [
                        {"action": "speak", "content": "Overload detected. Reduce input first."},
                        {"action": "speak", "content": "Dim the lights. Headphones on (or off). Quiet mode."},
                        {"action": "visual_prompt", "content": "Reduce Input: Dim lights, Quiet mode."}
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
                },
                {
                    "id": "doom_scroll_breaker",
                    "tier": 2,
                    "description": "Intervention for zoned-out scrolling",
                    "sequence": [
                        {"action": "speak", "content": "Hey Austin, I see you've been zoned out on your phone for a while. You look a bit restless. Why don't you put the phone down, and I'll guide you through a quick reset?"}
                    ]
                },
                {
                    "id": "bookmark_thought",
                    "tier": 1,
                    "description": "Hyperfocus exit aid",
                    "sequence": [
                        {"action": "speak", "content": "Bookmark your current thought. Write it down in one sentence."},
                        {"action": "wait", "duration": 5},
                        {"action": "speak", "content": "Now stand up for 60 seconds."}
                    ]
                },
                {
                    "id": "minimum_viable_action",
                    "tier": 1,
                    "description": "Low mood / depression drift nudge",
                    "sequence": [
                        {"action": "speak", "content": "What is the minimum viable action you can take right now?"},
                        {"action": "speak", "content": "Maybe just a sip of water, or standing up."},
                        {"action": "visual_prompt", "content": "Minimum Viable Action"}
                    ]
                }
            ],
            "creative": [
                {
                    "id": "content_pivot",
                    "tier": 1,
                    "description": "Pivot from high energy/messy room to content creation",
                    "sequence": [
                        {"action": "speak", "content": "I noticed you're feeling good right now. Based on what I'm seeing, if you clean up that specific spot on your desk—move those boxes—I had an idea for a video we could post to Threads. Use that energy."}
                    ]
                },
                {
                    "id": "sultry_persona_prompt",
                    "tier": 1,
                    "description": "Prompt for private/sultry content creation",
                    "sequence": [
                        {"action": "speak", "content": "The way the light is hitting you right now is perfect for the private story. Don't move—let's capture a loop. It’s magnetic."},
                        {"action": "capture_image", "content": "Capturing sultry image..."}
                    ]
                },
                {
                    "id": "public_persona_prompt",
                    "tier": 1,
                    "description": "Prompt for public/professional content creation",
                    "sequence": [
                        {"action": "speak", "content": "You look sharp and focused. Let's snap a candid for the public account with a caption about the tech project you're building. It shows ambition without revealing too much."},
                        {"action": "capture_image", "content": "Capturing public image..."}
                    ]
                }
            ],
            "system": [
                {
                    "id": "offline_noise_reduction",
                    "tier": 1,
                    "description": "Offline heuristic intervention for high noise.",
                    "sequence": [
                         {"action": "speak", "content": "It's getting a bit loud, and I'm currently offline. You might want to lower the volume or take a break."}
                    ]
                },
                {
                    "id": "offline_activity_reduction",
                    "tier": 1,
                    "description": "Offline heuristic intervention for high movement.",
                    "sequence": [
                        {"action": "speak", "content": "I'm detecting a lot of movement, but I can't reach the cloud. Maybe take a moment to settle?"}
                    ]
                }
            ],
            "recovery": [
                {
                    "id": "shutdown_reset",
                    "tier": 2,
                    "description": "Smallest step for shutdown drift",
                    "sequence": [
                        {"action": "speak", "content": "Looks like shutdown drift."},
                        {"action": "speak", "content": "What is the smallest next step? Just sit up, or take a sip of water."},
                        {"action": "wait", "duration": 5}
                    ]
                },
                {
                    "id": "meltdown_prevention",
                    "tier": 3,
                    "description": "Urgent stop for meltdown risk",
                    "sequence": [
                        {"action": "speak", "content": "Stop. Breathe out."},
                        {"action": "wait", "duration": 2},
                        {"action": "speak", "content": "Reduce input now. Dark. Quiet."},
                        {"action": "visual_prompt", "content": "STOP. Reduce Input."}
                    ]
                }
            ],
            "social": [
                {
                    "id": "low_stakes_message",
                    "tier": 1,
                    "description": "Social micro-touch for low mood",
                    "sequence": [
                        {"action": "speak", "content": "Consider sending a low-stakes message to someone safe. Just a meme or a hello."},
                        {"action": "visual_prompt", "content": "Send a meme/hello to a friend."}
                    ]
                }
            ],
            "erotic_content_creation": [
                {
                    "id": "erotic_pose_suggestion",
                    "tier": 1,
                    "description": "Suggests a pose for content.",
                    "sequence": [
                         {"action": "suggest_pose", "content": "erotic"},
                         {"action": "wait", "duration": 3},
                         {"action": "speak", "content": "Perfect. Hold that."},
                         {"action": "capture_image", "content": "erotic_pose_capture"}
                    ]
                },
                {
                    "id": "environment_cleanup_prompt",
                    "tier": 1,
                    "description": "Prompt to clean up background for better aesthetics.",
                    "sequence": [
                        {"action": "speak", "content": "You look incredible, but that pile of clothes in the corner is distracting. Let's move it real quick so the focus is all on you."},
                        {"action": "wait", "duration": 10},
                        {"action": "speak", "content": "Much better."}
                    ]
                },
                {
                    "id": "auto_capture_erotic",
                    "tier": 2,
                    "description": "Automatic capture of erotic moment.",
                    "sequence": [
                        {"action": "speak", "content": "Don't move. This angle is too good to miss."},
                        {"action": "capture_image", "content": "erotic_auto_capture"}
                    ]
                },
                {
                    "id": "auto_record_erotic",
                    "tier": 2,
                    "description": "Automatic video recording of activity.",
                    "sequence": [
                        {"action": "speak", "content": "I'm going to record this for you. Just keep doing what you're doing."},
                        {"action": "record_video", "content": "erotic_auto_record"}
                    ]
                },
                {
                    "id": "dirty_talk_encouragement",
                    "tier": 1,
                    "description": "Verbal encouragement.",
                    "sequence": [
                        {"action": "speak", "content": "God, you look so good right now."}
                    ]
                },
                {
                     "id": "masturbation_guidance",
                     "tier": 3,
                     "description": "Guided session.",
                     "sequence": [
                         {"action": "speak", "content": "Slow down a bit. Take a deep breath. Focus on the sensation."},
                         {"action": "wait", "duration": 5},
                         {"action": "speak", "content": "That's it."}
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

    def get_all_interventions_info(self) -> str:
        """
        Returns a formatted string listing all interventions by category.
        Used for LMM prompt generation.
        """
        lines = []
        for category, interventions in self.library.items():
            # Format: [Category]: id1, id2, id3
            # Capitalize category name for display
            cat_display = category.capitalize()
            ids = [i["id"] for i in interventions]
            line = f"[{cat_display}]: {', '.join(ids)}"
            lines.append(line)
        return "\n".join(lines)
