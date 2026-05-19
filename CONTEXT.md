# CrossRoads Domain

Domain language for the traffic intersection simulation.

## Language

**Intersection**:
The central road crossing where vehicle flows are coordinated by traffic lights.
_Avoid_: Crossroad, junction

**Arm**:
A directional approach of an Intersection that carries one inbound and one outbound lane flow.
_Avoid_: Approach, road branch

**Phase**:
A coordinated traffic-light window where a specific set of Arms is allowed to proceed.
_Avoid_: Cycle, stage

**Light State**:
The per-phase signal value that is exactly one of Green, Yellow, or Red at a given tick.
_Avoid_: Signal color, state

**Tick**:
The smallest simulation time unit used to advance Light State transitions.
_Avoid_: Frame, time step

**Major Cycle**:
One full ordered pass through all Phases in the Intersection.
_Avoid_: Cycle, round

**Phase Handoff**:
The transition point where one Phase completes and the next Phase becomes active.
_Avoid_: Phase switch, rotation step

**Stop Line**:
The line on an Arm where vehicles must wait when the Light State is not Green.
_Avoid_: Holding line, wait line

## Relationships

- An **Intersection** contains multiple **Arms**
- An **Intersection** advances through ordered **Phases**
- A **Phase** includes one or more **Arms**
- A **Phase** has one active **Light State** at any tick
- Each **Tick** may advance a **Phase** to the next **Light State**
- A **Major Cycle** contains every **Phase** exactly once
- A **Phase Handoff** occurs when the active **Phase** reaches Red
- Each **Arm** has one **Stop Line**

## Example dialogue

> **Dev:** "During a **Major Cycle**, does each **Phase** end with a **Phase Handoff**?"
> **Domain expert:** "Yes — when the active **Phase** reaches Red, we perform a **Phase Handoff** and the next Phase takes control at each **Stop Line**."

## Flagged ambiguities

- "crossroad" and "junction" were used for the same concept — resolved: use **Intersection**.
- "cycle" was used for both full rotation and one green window — resolved: use **Phase** for one window and **Major Cycle** for the full loop.
