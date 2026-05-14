from statemachine import StateChart, State
import random

#"to_state":"Washing","from_state":"Idle","sojourn_sec":9106}

class SimpleStateMachine(StateChart):
    "A State machine"
    state1 = State(initial=True)
    state2 = State()
    state3 = State()

    cycle = (
        state1.to(state2)
        | state1.to(state3)
        | state2.to(state3)
        | state3.to(state1)
    )

    def before_cycle(self, event: str, source: State, target: State):
        rn = random.randint(50, 100)
        data = {}
        data["to_state"] = target.id
        data["from_state"] = source.id
        data["sojourn_sec"] = rn
        return data


sm = SimpleStateMachine()
trans = sm.send("cycle")
print(trans)

# This example will only run on automated tests if dot is present
sm._graph().write_png("traffic_light.png")