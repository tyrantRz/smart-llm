# Task Description: Throw the Spatula in the trash

# GENERAL TASK DECOMPOSITION
# Decompose and parallelize subtasks where ever possible
# Independent subtasks:
# SubTask 1: Throw the Spatula in the trash. (Skills Required: GoToObject, PickupObject, ThrowObject)
# We can execute SubTask 1.

# CODE
def throw_spatula_in_trash():
    # 0: SubTask 1: Throw the Spatula in the trash
    # 1: Go to the Spatula.
    GoToObject('Spatula')
    # 2: Pick up the Spatula.
    PickupObject('Spatula')
    # 3: Go to the GarbageCan.
    GoToObject('GarbageCan')
    # 4: Throw the Spatula in the GarbageCan.
    ThrowObject('Spatula')

# Execute SubTask 1
throw_spatula_in_trash()

# Task throw the Spatula in the trash is done