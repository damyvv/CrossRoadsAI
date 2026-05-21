# CrossRoads Domain

Domain language for the traffic intersection simulation.

## Language

**Intersection**:
The central road crossing where vehicle flows are coordinated by traffic lights.
_Avoid_: Crossroad, junction

**Arm**:
A directional approach of an Intersection that carries one inbound lane group and one outbound lane group.
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

**Lane Width**:
The configured width of one lane used to size lane groups and place lane centerlines.
_Avoid_: Road width, carriageway width

**Carriageway Separation**:
The median gap between inbound and outbound lane groups on an Arm used to keep opposite lane centerlines straight through the Intersection.
_Avoid_: Verge spacing, median padding

**Lane Movement Set**:
The allowed movement options for a lane, represented as a non-empty subset of left, straight, and right.
_Avoid_: Turning mode, lane intent

**Inbound Lane Ordering**:
The driver-view left-to-right order of Inbound Lanes on an Arm, validated by movement priority left, then straight, then right.
_Avoid_: Screen-space order, arbitrary lane order

**Signal Group**:
The set of lanes that share one traffic-light window because their lane movements are mutually conflict-free.
_Avoid_: Phase lane set, lane batch

**Clearance Interval**:
The all-red duration between consecutive Signal Groups used to clear conflicting movement paths.
_Avoid_: Dead time, empty phase

**Committed Movement**:
The single movement choice assigned to a Vehicle at spawn and kept unchanged for the rest of its traversal.
_Avoid_: Dynamic intent, opportunistic turn

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
- A **Phase Handoff** may include a **Clearance Interval** before the next **Signal Group** turns Green
- Each **Arm** has one **Stop Line**
- Each **Arm** has an **Inbound Lane** determined by **Driving Side**
- Each **Arm** defines one **Inbound Lane Ordering**
- Each **Inbound Lane** has one **Lane Centerline**
- Each **Inbound Lane** has one **Lane Movement Set**
- Each **Inbound Lane** belongs to exactly one **Signal Group** per **Phase**
- A **Vehicle** receives one **Committed Movement** at spawn from its lane's **Lane Movement Set**
- Each **Arm** has one **Carriageway Separation** between inbound and outbound lane groups
- **Carriageway Separation** keeps opposing **Lane Centerline** paths collinear through an **Intersection**
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
- "verge spacing" was used for geometric lane alignment — resolved: use **Carriageway Separation**.
- "turning lane" and "shared lane" were overloaded — resolved: define allowed movements as **Lane Movement Set**.
- "left-to-right lane order" was ambiguous between driver-view and screen-space — resolved: use driver-view **Inbound Lane Ordering**.
- "traffic light per lane" was interpreted as either independent or coordinated control — resolved: model lanes under coordinated **Signal Groups**.
- "all-red time" overlapped with yellow semantics — resolved: use **Clearance Interval** for inter-group red-only time.
- "intent" was used as both configurable options and runtime choice — resolved: use **Lane Movement Set** for options and **Committed Movement** for per-vehicle choice.
- "Arm" implied single-lane flow while planning multi-lane support — resolved: **Arm** contains lane groups, not single lanes.
