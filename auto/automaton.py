import random
import itertools
from auto.board import Board
from auto.pad import Pad
import numpy as np

"""
    :module:: automaton
    :platform: Unix, Windows
    :synopsis: The AI/Computer Player object for the game of Clue-Less.

    :moduleauthor: Ethan Wilansky, Shambhavi Sanskrit and Henoke Shiferaw

"""


class Player:
    """
    The player class to be instantiated for each requested Clue-Less computer/AI player

    """
    _board = Board()

    # _player_count class variable enforces the maximum # of players allowed. See IndexError in constructor
    _player_count = 0

    def __init__(self, player_id, available_suspects_list, total_players):
        """
        Instantiate a player for the game and provided that the upper-limit of
        allowed players has not been reached.

        :param player_id: the id assigned to this player by the caller (p01 - p06)
        :param available_suspects_list [list <string>]
        :param total_players: int

        :var
            class vars:
            _board: networkx.Graph
            _player_count: int
            instance vars:
            _selected_suspect: string
            _location: string
            _prior_moves: set<string>
            _pad: dictionary<auto.PlayerMatrix
            player_id: string

        :raise
            IndexError if player count > 5
        """

        if self._player_count <= 5:

            # add to the player count so server knows # active autonomous player
            self._player_count += 1

            # instance variables needed for game play
            self._selected_suspect = self._get_player(available_suspects_list)
            # to start, the _location is the starting position for this player based on selected suspect
            self._location = self._get_starting_location(self._selected_suspect)

            # prior moves set will initially contain just the starting position for this player
            self._prior_moves = {self._location}
            # create a player _pad for this player with the total number of players specified
            self._pad = Pad(total_players)
            # get the cards for various private functions
            self._cards = self._pad.get_player_table(player_id).axes[0].tolist()

            self.player_id = player_id

        else:
            raise IndexError('no more than 5 computer players allowed')

    def receive_cards(self, dealt_cards):
        """
        Receive a set of cards from the dealer and store them.

        :param dealt_cards: list
        :return:  dealt cards
        :rtype: list<str>
        :raise:
            IndexError if # of cards not between 3 and 6
            ValueError if cards dealt are not in Cards data structure
        """
        # if 3 <= len(dealt_cards) <= 6:
        # self.dealt_cards = dealt_cards
        # else:

        if not 3 <= len(dealt_cards) <= 6:
            raise IndexError('the number of cards dealt, must be between 3 and 6')

        for card in dealt_cards:
            verified = self._verify_card(card)
            if not verified:
                raise ValueError('the card {0} is not valid'.format(card))

        self._mark_my_cards_on_pad(dealt_cards)

    def update(self, game_state):

        # TODO: get the actual game_states sent to update via the game_state param in a docstring. Get rid
        # of other stuff here. Don't update until message format has settled.
        # example game_state for taking a turn that includes a suggestion
        # {‘move’: ’Study’, ’suggestion’: {‘from_player’: ‘p01’, ‘cards’: {’Mustard’, ‘Lounge’, ’Rope’}}}

        # example game_state for letting the player who made a suggestion know of a response (directed answer)
        # {‘move_made’: True, ’answer’: {‘from_player’: ‘p02’, ‘card’: ‘Mustard’}}
        # example game_state for letting other players know of a response (undirected answer)
        # {‘answer’: {‘from_player’: ‘p02’, ‘has_card’: True, ’suggestion’: {’Plum’, 'Hall‘, 'Candlestick’}}}

        # server sends an update and directs the question to one of the players in each update. The server knows
        # the player order and therefore the order in which the suggestion should be asked. For the autonomous
        # players, only the player listed in to_player will respond to the update call in this case
        if 'suggestion' in game_state:
            suggestion = game_state['suggestion']
            if 'to_player' in suggestion and suggestion['to_player'] == self.player_id:
                return self._answer(game_state['suggestion']['cards'])

        if 'answer' in game_state:
            accusation = self._mark_pad(game_state)
            if not accusation:
                return {'turn_complete': True}
            else:
                return {'accusation': {'from_player': self.player_id, 'cards': accusation}, 'turn_complete': True}

        # move was unsuccessful. Return to take_turn and try another move
        if 'make_move' in game_state and not 'make_move':
            pass  # not implemented yet


    def take_turn(self, game_state):

        # move block
        """
        Take a turn given the game state.

        :param game_state: dictionary containing the state of the game position, suggestion and accusation keys.
          Key values are dictionaries as described in the interface specification.
        :return: dictionary containing a moveto, suggest and accuse key. Suggest and accuse values are lists of string
        """

        available_moves = self._filter_moves(game_state)
        turn_response = self._make_move(available_moves)

        # call make_suggestion here. Make accusation is handled in update. Not sure if it needs to also
        # be called from here. Will check later
        # turn_response = self._make_suggestion(turn_response)

        return turn_response

    # @property
    # def _get_suspects(self):
    #     """
    #     Get the suspects that are valid for this game.
    #
    #     :return: valid suspects
    #     :rtype: set<str>
    #     """
    #     return {'Mustard', 'Scarlet', 'White', 'Plum', 'Green', 'Peacock'}

    @property
    def _get_rooms(self):
        """
        Get the rooms that are valid for this game.

        :return: valid rooms
        :rtype: set<str>
        """
        return {'Study', 'Hall', 'Lounge', 'Library', 'Billiard', 'Dining', 'Conservatory', 'Ballroom', 'Kitchen'}

    # @property
    # def _get_weapons(self):
    #     """
    #     Get the weapons that are valid for this game.
    #
    #     :return: valid weapons
    #     :rtype: set<str>
    #     """
    #     return {'Knife', 'Wrench', 'Revolver', 'Pipe', 'Rope', 'Candlestick'}

    @property
    def _get_location(self):

        """
        Get the _location of this player and store it as an instance variable for tracking _location.

        :return: current _location
        :rtype: str
        """
        return self._location

    def _set_location(self, game_state):
        """
        Sets the current _location based on the game_state returned by the caller/server

        :param game_state: {'positions': {<pid>: <_location>, ...}}
        :return:
        """

        self._location = game_state['positions'][self.player_id]
        self._prior_moves.add(self._location)

    def _verify_card(self, card_to_verify):

        """
        Verify that the card dealt is valid

        :param: card_to_verify <string>
        :return: true if card is valid. Otherwise, false
        :rtype: bool
        """
        # all_cards = self._get_suspects.union(self._get_rooms.union(self._get_weapons))
        # all_cards = list(itertools.chain(*cards))

        if card_to_verify in self._cards:
            return True
        else:
            return False

    def _next_moves(self, current_location):
        """
        Finds all possible locations that can be the next move from the player's current position.

        :param current_location:
        :return: a list of possible next moves
        :rtype: list<str>
        """
        return self._board.neighborhood(current_location, 1)

    def _filter_moves(self, game_state):

        """
        Remove moves that are blocked and favor moves that haven't been taken.

        :param game_state:
        :return: a available, non-blocked move
        :rtype: set<str>
        """
        # set current _location to the position reported in game_state
        self._set_location(game_state)
        # get the possible next moves, given the current _location
        next_moves = self._next_moves(self._location)
        # get this player's prior moves
        prior_moves = self._prior_moves
        # get current positions of all players
        occupied_locations = game_state['positions'].values()

        # if next moves is a position currently occupied by another player or next moves contains a match with
        # prior moves, then it's not an available move or a favored move from the set of possible moves.
        available_moves = next_moves.difference(occupied_locations)
        available_moves = available_moves.difference(prior_moves)

        # if available_moves is an empty set, then randomly select an available move if there is one available
        if not available_moves:
            possible_moves = next_moves.difference(occupied_locations)
            if len(possible_moves) > 0:
                pick_me = random.sample(possible_moves, 1)
                available_moves.add(pick_me[0])

        return available_moves

    def _make_move(self, available_moves):

        """
        Make a move

        :param available_moves:make
        :return: a dictionary containing the move command and a _location to move or empty string
        :rtype : dict{'move':<str>} example: {'move': 'Kitchen'}

        """
        turn_response = {'move': ''}

        for move in available_moves:
            if move not in self._prior_moves:
                # populate the move key with this move (will be sent to caller)
                turn_response['move'] = move
                # add the move to prior moves list
                self._prior_moves.add(move)
                return turn_response
            elif move in self._prior_moves:
                # take this move if it's available even if it has already been taken. Nothing else to do
                turn_response['move'] = move
                return turn_response

        return turn_response

    def _make_suggestion(self, move_selected):

        # moved to a room, can make suggestion
        if move_selected['move'] in self._get_rooms:
            # check the pad to see what cards are unknown
            cards = self._get_unknown_cards()
            # except for the room card, pick two unknown cards, one suspect, one weapon
            # if there is only one category of unknown card, choose one of your cards in the known
            # card category to trip-up opponents
        #TODO: working on this function

    def _answer(self, suggestion):

        """
        Ask this computer player a question about whether they have one of three cards

        :param suggestion: list<string> containing three valid card values.

        :return: string containing a valid card value or no_match
        """

        cards = self._pad.get_player_table(self.player_id)['c1']

        # improve this by preferring not to return room cards because there are more
        # room cards than any other cards. Helps to keep the other players guessing.
        # might want to create a stack where the first items in are rooms so that rooms would
        # be the last items that are popped off the stack in an answer
        for card in suggestion:
            if card in cards[cards == 1]:
                return card

        return 'no_match'

    def _mark_my_cards_on_pad(self, dealt_cards):

        """
        Mark the cards this player was dealt.

        :type dealt_cards: list
        :param dealt_cards: 
        """
        player_tbl = self._pad.get_player_table(self.player_id)

        for card in dealt_cards:
            # get this player's sub-table and mark that they have this set of cards (from 3 to 6)
            player_tbl['c1'][card] = 1

    def _mark_pad(self, game_state):

        # three possible suggestions are: True ("I have one of the cards suggested") if this player is not the one
        # making the suggestion. False, ("I don't have one of the cards suggested") whether or not this player is
        # the one making the suggestion. The actual card if this player is the one making the suggestion and there is
        # a match to share.

        """
        Given the suggestion, mark this player's _pad.
        :param game_state:
        """

        # example game_state for letting other players know of a response (undirected answer)
        # {'answer': {'has_card': True, 'from_player': 'p02'}, 'suggestion': ['Plum', 'Hall', 'Candlestick']}

        answer = game_state['answer']
        responding_player = answer['from_player']
        # for the current player, get the sub-table for the responding player
        responding_player_tbl = self._pad.get_player_table(responding_player)

        if 'has_card' in answer and answer['has_card'] is True:
            suggestions = game_state['cards'].copy()
            card01 = suggestions.pop()
            card02 = suggestions.pop()
            card03 = suggestions.pop()

            # get the tracking cell lists
            cell01 = responding_player_tbl['c2'][card01]
            cell02 = responding_player_tbl['c2'][card02]
            cell03 = responding_player_tbl['c2'][card03]

            # check if any of the cards have been asked of this player before. If so, add the greatest increment
            # to each of the cells. This is done here by getting the length of the union of the cells and adding 1
            new_entry = len(cell01.union(cell02.union(cell03))) + 1
            cell01.add(new_entry)
            cell02.add(new_entry)
            cell03.add(new_entry)

        elif 'has_card' in answer and answer['has_card'] is False:
            pass  # no one has the suggested cards. It might be time to make an accusation
        else:
            card_provided = answer['card']

            # locate player 1's column 1 for the specified card and put a 1 in it
            # TODO: if c1 is already checked somewhere else then this is either a lie or a code bug.
            # must deal with this condition in code.
            responding_player_tbl['c1'][answer['card']] = 1

            self._clear_c2_cells(card_provided)

        # this will only return a set of cards if it's time to accuse
        return self._analyze_table_to_accuse()

    def _clear_c2_cells(self, card_provided):
        # clear the corresponding col2 cell for the answered card
        # and do this for all of the players including this player
        for player in self._pad.players_list:
            tbl = self._pad.get_player_table(player)
            tbl['c2'][card_provided].clear()

    def _get_player(self, available_players_list):
        """
        Randomly choose a player from a list of available players. This determines starting position on _board.

        :param available_players_list:list
        :return: a randomly selected player
        :rtype : str
        """
        return random.choice(available_players_list)

    def _get_starting_location(self, selected_player):
        """
        Gets the starting position of the selected player.

        :param selected_player <string>
        :return: the selected player's starting hallway position
        :rtype : str
        """
        starting_positions = {
            'Scarlet': 'Hallway_02',
            'Mustard': 'Hallway_03',
            'White': 'Hallway_05',
            'Green': 'Hallway_06',
            'Peacock': 'Hallway_07',
            'Plum': 'Hallway_08'
        }

        return starting_positions[selected_player]

    def _analyze_table_to_accuse(self):

        # get all of the cards
        cards = self._pad.get_player_table(self.player_id).axes[0].tolist()

        unverified_cards = self._get_unknown_cards()

        if len(unverified_cards) == 3:
            return unverified_cards

    def _get_unknown_cards(self):
        """
        Get the cards that aren't marked in a player's tracking pad

        :param cards: list of all cards in deck
        :return: unknown cards
        """

        # get this player's pad
        pad = self._pad

        # get all of the cards in the game
        cards = self._pad.get_player_table(self.player_id).axes[0].tolist()

        # create a set to hold unverified cards
        unverified_cards = set()

        # for each card, check each c1 cell sub-table. If not checked, add it to unverified_cards
        for card in cards:
            i = 0
            for key in pad.player_pad.keys():
                if pad.get_player_table(key).c1[card] == 1:
                    break
                else:
                    # the cell must not be marked
                    # if self._pad.get_player_table(key).c1[card] == np.nan:
                    i += 1

                if i == 4:
                    unverified_cards.add(card)


        return unverified_cards
