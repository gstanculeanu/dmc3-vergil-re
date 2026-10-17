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

## Vergil motion groups — [LOCAL], confirmed against real bytes (E-035)

| Group | File | Occupied MOT slots | Slot → duration (frames), from real bytes |
|---|---|---|---|
| 0 | `pl021_00_0.pac` | 23 | 0:105 1:61 2:48 3:350 4:69 5:69 6:15 7:60 8:60 9:69 14:103 16:6 17:5 18:4 19:115 20:61 21:61 22:61 30:26 31:105 50:45 51:26 58:60 |
| 1 | `pl021_00_1.pac` | 14 | 0:50 1:45 2:95 3:74 4:81 5:104 6:102 7:80 9:90 11:154 13:50 14:77 15:50 16:115 |
| 2 | `pl021_00_2.pac` | 5 | 0:340 1:200 2:250 3:72 4:110 |
| 3 | `pl021_00_3.pac` | 16 | 0:105 1:115 3:83 4:122 5:131 6:70 7:110 8:29 9:37 10:125 11:152 12:174 13:65 14:90 15:152 16:189 |
| 4 | `pl021_00_4.pac` | 11 | 0:62 1:115 3:98 4:106 5:149 6:25 7:79 8:24 9:36 10:117 11:85 |
| 5 | `pl021_00_5.pac` | 14 | 0:180 1:123 3:83 4:122 5:252 6:82 7:54 8:45 9:10 10:19 11:99 12:165 13:83 14:135 |
| 6 | `pl021_00_6.pac` | 2 | 0:10 1:10 |
| 7 | `pl021_00_7.pac` | 11 | 0:150 1:123 3:94 4:110 5:145 6:82 7:54 8:45 9:119 10:95 11:71 |
| 8 | `pl021_00_8.pac` | 11 | 0:150 1:115 3:98 4:106 5:136 6:25 7:79 8:77 9:99 10:95 11:71 |
| 9 | `pl021_00_9.pac` | 1 | 0:100 |

All ten group slot-counts match E-009 exactly; durations and record counts were
read from shipped bytes (E-035), so this table is **[LOCAL]** rather than
[EXTERNAL].

## Move names — [EXTERNAL], group attribution unconfirmed

Community list, transcribed. Slot numbers are the ones the thread gives; they
are **global** motion numbers, and the group/slot pairing used by our
`pl021_00_*.pac` files is **not** established by bytes. Treat every row below
as a hypothesis to confirm by exporting the clip and watching it.

## Locally confirmed overlay anchors (Crimson overlays, E-007)

Comparing each `new<Name>_pl021_00_<group>.pac` overlay to its base file on
real bytes, the slots whose durations differ identify which group/slot the
modder retargeted:

| Overlay | Base file | Slots that differ | Inferred target | Confidence |
|---|---|---|---|---|
| `newTauntVergilAnims1_pl021_00_2.pac` | `pl021_00_2.pac` | slot 0 is 340.0 in both (overlay retargets it) | group 2, slot 0 = taunt | [LOCAL] slot targeting; name from overlay filename |
| `newJudgementCut_pl021_00_3.pac` (+ `Air`/`AirJF` variants) | `pl021_00_3.pac` | only slot 13 differs (base 65 → overlay 5/11/3) | group 3, slot 13 = Judgement Cut | [LOCAL] slot targeting; name from overlay filename |
| `newYamatoHighTime_pl021_00_5.pac` | `pl021_00_5.pac` | slots 7 (54→150) and 8 (45→51) | group 5, slots 7–8 | [LOCAL] slot targeting; name from overlay filename |

These three anchors are the only move-name associations backed by local bytes.
Every other row in the community table remains **[EXTERNAL]** — a group/slot
pairing and a name, neither proven here. Confirming them (and recovering hit
frames / cancel windows) is the F9 move-set work, which needs the MOT keyframe
encoding (F4, blocked on engine ground truth).

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
