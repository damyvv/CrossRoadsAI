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

**Vehicle**:
A simulated road user that traverses an Arm toward and through an Intersection.
_Avoid_: Car entity, sprite

**Driving Side**:
The lane-side convention used by the simulation for traffic flow.
_Avoid_: Traffic side, handedness

**Inbound Lane**:
The lane on an Arm used by vehicles entering the Intersection according to the Driving Side.
_Avoid_: Approach line, travel strip

**Lane Centerline**:
The longitudinal path at the center of a lane used as the canonical movement path for vehicles.
_Avoid_: Center path, lane track

**Exit Boundary**:
The opposite-direction Stop Line crossing point where a Vehicle is considered to have exited the Intersection traversal.
_Avoid_: End line, despawn line

**Exited State**:
The traversal state after a Vehicle passes the Exit Boundary but before it is outside the visible window.
_Avoid_: Completed state, done state

**Discard State**:
The post-visibility lifecycle state where a Vehicle is fully outside the visible window and ready for removal.
_Avoid_: Cleanup state, delete state

## Relationships

- An **Intersection** contains multiple **Arms**
- An **Intersection** advances through ordered **Phases**
- A **Phase** includes one or more **Arms**
- A **Phase** has one active **Light State** at any tick
- Each **Tick** may advance a **Phase** to the next **Light State**
- A **Major Cycle** contains every **Phase** exactly once
- A **Phase Handoff** occurs when the active **Phase** reaches Red
- Each **Arm** has one **Stop Line**
- Each **Arm** has an **Inbound Lane** determined by **Driving Side**
- Each **Inbound Lane** has one **Lane Centerline**
- A **Vehicle** follows the **Lane Centerline** of an **Inbound Lane** on an **Arm**
- A **Vehicle** leaves the simulation at the **Exit Boundary**
- A **Vehicle** can be in **Approaching**, **Crossing**, **Exited State**, or **Discard State**
- A **Vehicle** enters **Exited State** after crossing the **Exit Boundary**
- A **Vehicle** enters **Discard State** when fully outside the visible window

## Example dialogue

> **Dev:** "During a **Major Cycle**, does each **Phase** end with a **Phase Handoff**?"
> **Domain expert:** "Yes — when the active **Phase** reaches Red, we perform a **Phase Handoff** and the next Phase takes control at each **Stop Line**."

## Flagged ambiguities

- "crossroad" and "junction" were used for the same concept — resolved: use **Intersection**.
- "cycle" was used for both full rotation and one green window — resolved: use **Phase** for one window and **Major Cycle** for the full loop.
- "constant green traversal" conflicted with "mandatory stop-at-stop-line" — resolved: keep **constant green traversal** for slice #4.
- "EXITED" was conflated with "off-screen disappearance" — resolved: **Exit Boundary** is opposite-direction Stop Line crossing, while off-screen disappearance is a separate rendering/lifecycle concern.
