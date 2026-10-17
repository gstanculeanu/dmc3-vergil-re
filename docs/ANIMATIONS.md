# Vergil's move set — animation map

An enemy is defined by its moves. This file maps DMC3's motion slots to the moves
they contain, so an exported animation is not just `slot037`.

## Confidence levels

- **[LOCAL]** reproduced in this install (slot counts, durations from E-009).
- **[EXTERNAL]** taken from the community motion-identification thread below and
  **not yet verified here**. Treat every row below as a hypothesis to confirm by
  exporting the clip and watching it.
- **[UNKNOWN]** no name yet.

## Where the names come from

Infernal Works, *File ID / Motion Identification thread* —
<https://infernalwarks.boards.net/thread/248/file-motion-identfication-thread>

The community has already decoded a large part of DMC3's motion naming, including
Vergil's. That thread is the source of the tables below. Verifying it against our
own exports is issue **F7**.

Also useful as ground truth: the Crimson overlays in this install are named after
the move they patch (`newJudgementCut_pl021_00_3.pac`,
`newYamatoHighTime_pl021_00_5.pac`, `newRisingStar_pl021_00_4.pac`), so the slot
they replace carries that move (E-007).

## Vergil motion groups — [LOCAL]

| Group | File | Occupied MOT slots |
|---|---|---|
| 0 | `pl021_00_0.pac` | 23 |
| 1 | `pl021_00_1.pac` | 14 |
| 2 | `pl021_00_2.pac` | 5 |
| 3 | `pl021_00_3.pac` | 16 |
| 4 | `pl021_00_4.pac` | 11 |
| 5 | `pl021_00_5.pac` | 14 |
| 6 | `pl021_00_6.pac` | 2 |
| 7 | `pl021_00_7.pac` | 11 |
| 8 | `pl021_00_8.pac` | 11 |
| 9 | `pl021_00_9.pac` | 1 |

## Move names — [EXTERNAL], group attribution unconfirmed

Community list, transcribed. Slot numbers are the ones the thread gives.

| Slot | Move |
|---|---|
| 000 | resting / panting after deactivating Super DT (Vergil 3 phase 3) |
| 001 | Yamato Combo, 1st strike |
| 002 | Yamato Combo, 2nd strike |
| 003 | Yamato Combo, 3rd (final) strike |
| 004 | Upper Slash |
| 005 | Downward Slash |
| 006 | Rising Sun |
| 007 | Rapid Slash — startup |
| 008 | Rapid Slash — dash |
| 009 | Rapid Slash — end |
| 010 | slide back into Judgement Cut stance |
| 011 | Judgement Cut |
| 012 | return to idle after Judgement Cut |
| 013 | step back after taking maximum damage (Vergil 3) |
| 014 | sheathe Yamato after Yamato Combo |
| 015 | raise hand to parry, then counter-attack |
| 016 | Super DT deactivate → rest and pant |
| 017 | Air Trick — prepare |
| 018 | Air Trick — during/after |
| 019 | Yamato Taunt (human form, immunity sphere) |
| 020 | Yamato Taunt (DT, raises head) |
| 021 | walk backwards |
| 022 | walk right |
| 023 | walk left |
| 024 | Beowulf Combo, 1st strike (Vergil 2) |
| 025 | Beowulf Combo, 2nd strike (Vergil 2) |
| 026 | Beowulf Combo II — flurry of kicks (Beehive-style) |
| 027 | Beowulf Combo II — end of flurry |
| 028 | Starfall (Vergil 2) |
| 029 | land after Starfall (Vergil 2) |
| 030 | Force Edge Combo, last attack (Vergil 3) |
| 031 | Stinger — initiate (Vergil 3) |
| 032 | Stinger — dash |
| 033 | Stinger — end |
| 034 | Round Trip (Vergil 3) |
| 035 | Judgement Cut Storm — stance |
| 036 | Judgement Cut Storm |
| 037 | return and kneel after Judgement Cut Storm |
| 038 | kneel continued |
| 039 | stand up → Chiburi → sheathe Yamato |
| 040 | Helm Breaker (Vergil 3) |
| 041 | switch weapon animation (DMC1 Dante stomp) for Vergil 2 |
| 042 | Beowulf Combo, 3rd (final) strike (Vergil 2) |
| 043 | spin Yamato to deflect/block all incoming damage |
| 044 | sheathe Yamato after the deflect spin |

### Also listed for other players

The same thread documents `pl000_00` (Dante) and damage-reaction slots, e.g.:

| Slot | Move |
|---|---|
| 000 | take damage from the front |
| 001 | take damage from the back |
| 002 | step back after maximum damage (Vergil 1) |
| 004 | dying in Bloody Palace |
| 005 | step back after maximum damage (Vergil 2) |
| 006 | after being parried (Vergil 3, Force Edge) |
| 007 | after being parried (Vergil Yamato / Vergil 2 Beowulf) |

## Why this matters for the enemy goal

An **enemy** needs, at minimum: an approach, an idle, a set of attacks with
recovery windows, a block/parry, a stagger, and a death. The list above already
contains most of Vergil's attacks, his parry (015, 043) and his taunts (019, 020).
What is still missing is the *timing* — where in each clip the hit lands (F9).

## Open items

* Confirm each row by exporting the clip (F7).
* Recover hit frames, cancel windows and state transitions per move (F9).
* Vergil has **two weapons** in DMC3 (Yamato, Beowulf, plus Force Edge in the
  fights) — record which moves belong to which weapon.
* Decide which subset an enemy AI can actually use, given G6 (Vergil will inherit
  a GoW3R enemy's AI, which may only drive a fixed set of states).
