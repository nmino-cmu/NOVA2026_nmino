# Speaker notes — GU-R01-20261107-r4

Opening: Ghost Users investigates browser workflows and keeps the evidence behind its answers. Here the task is to reach checkout with exactly one mug, without placing an order.

Setup: We declare the starting state, allowed interactions, goal checks and budget before the run.

Investigation: The browser runs locally. The model picks one of the controls on the page. Ordinary local code stores the observations, the costs, and the history.

Verification: This result is one witnessed sequence. Ghost Users resets the shop and replays those exact actions. The live run run_c6252c9a4a6e4ba2 verified 6 interactions. The first click was Express Nova Mug. The cart check did not pass on that click. The later catalog steps did, and the whole sequence passed on replay. Stop reason: completed_target.

Express check: A separate fixture check repeats only Express. The screen can say checkout is ready. The registered check fails because the cart is empty. That check is run_f14d218e9d8c4dff.

Close: This release is self-hostable and includes its evidence. These results apply to this task, this build, and this budget. This release does not search for a shorter route, and it does not claim the six-step path is optimal.
