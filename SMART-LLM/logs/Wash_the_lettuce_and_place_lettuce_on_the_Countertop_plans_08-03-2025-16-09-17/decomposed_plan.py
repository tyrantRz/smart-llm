# Task Description: Wash the lettuce and place lettuce on the Countertop

# GENERAL TASK DECOMPOSITION
# Decompose and parallelize subtasks where ever possible
# Independent subtasks:
# SubTask 1: Wash the Lettuce. (Skills Required: GoToObject, PickupObject, PutObject, SwitchOn, SwitchOff)
# SubTask 2: Place the washed Lettuce on the Countertop. (Skills Required: GoToObject, PickupObject, PutObject)
# We can execute SubTask 1 first and then SubTask 2, since they cannot be parallelized.

# CODE
def wash_lettuce():
    # 0: SubTask 1: Wash the Lettuce
    # 1: Go to the Lettuce.
    GoToObject('Lettuce')
    # 2: Pick up the Lettuce.
    PickupObject('Lettuce')
    # 3: Go to the Sink.
    GoToObject('Sink')
    # 4: Put the Lettuce inside the Sink.
    PutObject('Lettuce', 'Sink')
    # 5: Switch on the Faucet to wash the Lettuce.
    SwitchOn('Faucet')
    # 6: Wait for a while to let the Lettuce wash.
    time.sleep(5)
    # 7: Switch off the Faucet.
    SwitchOff('Faucet')
    # 8: Pick up the washed Lettuce.
    PickupObject('Lettuce')

def place_lettuce_on_countertop():
    # 0: SubTask 2: Place the washed Lettuce on the Countertop
    # 1: Go to the Countertop.
    GoToObject('CounterTop')
    # 2: Place the Lettuce on the Countertop.
    PutObject('Lettuce', 'CounterTop')

# Execute SubTask 1
wash_lettuce()

# Execute SubTask 2
place_lettuce_on_countertop()

# Task wash the lettuce and place lettuce on the Countertop is done