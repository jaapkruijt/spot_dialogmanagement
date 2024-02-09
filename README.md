# Spotter Dialog Management

## DialogManager

The dialog manager keeps track of the state of the dialog, represented by `spot.dialog_manager.State`, which contains:
* conv_state: State of the conversation in the Game (see flow-chart and `spot.dialog_manager.ConversationalState`)
* game_start: Statements of the game introduction
* intro: Statements of the game introduction round
* round: Round number
* position: The position currently discussed
* utterance: Last utterance of the human 
* mention: mention extracted fromt the utterance
* disambiguation_result: Result of the disambiguator
* confirmation: Status during confirmation requests

Transitions between states are accomplished by actions, which consist of an optional response message and a flag if
external input is required. Transistions and the related actions are determined by the `spot.dialog_manager.State#act`
method, which determines the follow-up state and action based on the current state and eventual external input.

On external input processing of state transitions and the related actions is triggered and performed until the action
signals to wait for further external input.

External input can be an utterance from the humann player or an event published by the SPOTTER game.

## Example script

Run `examples/interactive_game.py`. It will ask for Human input, enter:
* your statements there
* if input from the game is expected, prefix it with `game:` (currently the value after the colon only needs to be non-empty)