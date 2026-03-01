Making ai mafia game in discord

## TTS model preload (important for production)

Chatterbox downloads model weights on first load. If this happens while the bot is running in voice, Discord heartbeat can be blocked.

Warm the model cache before starting the bot:

```bash
python scripts/preload_tts_model.py
```

By default, the bot now preloads TTS before connecting to Discord. To disable that behavior:

```bash
PRELOAD_TTS_MODEL=0 python bot.py
```

One Game Server
  controlling
Ten LLM-driven agents
  inside
One Discord bot

Night: 30s
Detective: 20s
Doctor: 20s
Day debate: 60s

NIGHT_KILLER
→ NIGHT_DETECTIVE
→ NIGHT_DOCTOR
→ DAY_DISCUSSION
→ DAY_VOTE
→ CHECK_WIN
→ repeat

start_game()
├── get_agents()                    # Load from DB
├── GameEngine.create_game()         # Insert games table
├── GameEngine.add_agents_to_game()  # Insert game_players
├── GameEngine.assign_roles()        # Update roles
├── SQL query                        # Load roles + names
├── Create Player objects
├── Create GameState
└── active_games[channel_id] = game_state

start_phases()
└── phase_loop()

phase_loop()
├── For DAY/EVENING/MORNING:
│   └── run_phase_chat()
│       ├── get_alive_players()
│       ├── get_agents()
│       ├── build_prompt()
│       ├── ask_ollama()
│       ├── channel.send()
│       └── speak()
│
└── For NIGHT:
    ├── collect_night_actions()
    │   ├── get_alive_players()
    │   ├── build_night_decision_prompt()
    │   ├── ask_ollama()
    │   └── Parse responses
    │
    ├── resolve_night_logic()
    │   └── game_state.kill_player()  # Memory update
    │
    ├── GameEngine.resolve_night()    # DB update
    │
    ├── channel.send()                 # Announce death
    │
    └── game_state.check_win_condition()
        └── del active_games[channel.id] if winner


DAY
  ├── MORNING DISCUSSION (60s) → All agents talk
  └── MORNING VOTING (20s) → All agents vote

EVENING
  ├── EVENING DISCUSSION (30s) → All agents talk (doctor listens)
  └── EVENING ACTION (10s) → Doctor saves

NIGHT
  ├── NIGHT DISCUSSION (30s) → All agents talk (killer blends)
  └── NIGHT ACTION (20s) → Killer kills + Detective investigates
