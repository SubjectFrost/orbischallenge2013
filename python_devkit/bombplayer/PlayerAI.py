#Player.py ai
import random

from sys import stderr
from bombmanclient.Client import *
from Enums import *
from Direction import *

# constants for objective function
BDIST=-4 # closeness to bomb penalty
BRANGE=-1 # range of closest bomb penalty
BTIME=-1 # time left in closest bomb penalty
ODIST=-3 # opponent closeness penalty
OMOM=-1 # opponent momentum penalty
PDIST=3 # powerup bonus
TDIST=-2 # trap closeness penalty
BLDIST=2 # block closeness bonus

class PlayerAI():

	
	def manhattan_distance(self, start, end):
		'''
		Returns the Manhattan distance between two points. 

		Args:
			start: a tuple that represents the coordinates of the start position. 
			end: a tuple that represents the coordinates of the end postion
		'''
		return (abs(start[0]-end[0])+abs(start[1]-end[1]))

	def get_explode_time(self,bomb,bombs):
		# check if there are any bombs close by
		# bomb is tuple, a key of bombs
#		return bombs[bomb]['time_left']
		rnge = bombs[bomb]['range']
		bombs_new = bombs.copy()
		bombs_new.pop(bomb)
		t = [bombs[bomb]['time_left']]
		t += [self.get_explode_time((bomb[0]+x,bomb[1]),bombs_new) for x in range(-rnge-1,rnge+1) if bombs_new.has_key((bomb[0]+x,bomb[1]))]
		t += [self.get_explode_time((bomb[0],bomb[1]+y),bombs_new) for y in range(-rnge-1,rnge+1) if bombs_new.has_key((bomb[0],bomb[1]+y))]
		return min(t)

	def get_value(self, pos, oldpos, map_list, bombs, powerups, other_index, bombMove):
		if bombMove and pos == oldpos:
			return -100000
		t=0
		if len(bombs):
			t += BDIST*1.0/min(max(0.1,self.manhattan_distance(pos,bomb)+BTIME*(15-bombs[bomb]['time_left'])+BRANGE*bombs[bomb]['range']) for bomb in bombs)
		if len(self.blocks):
			t += BLDIST*1.0/min(self.manhattan_distance(pos,block) for block in self.blocks)
		if len(powerups):
			a = min(self.manhattan_distance(pos,powerup) for powerup in powerups)
			if not a:
				t += PDIST
			else:
				t += PDIST*1.0/a
		return t
	
	def __init__(self):
		self.blocks = []
		self.move = None
		self.bombMove = False

	def new_game(self, map_list, blocks_list, bombers, player_index):
		'''
		Called when a new game starts.
		
		map_list: a list of lists that describes the map at the start of the game

			e.g.
				map_list[1][2] would return the MapItem occupying position (1, 2)

		blocks_list: a list of tuples which indicates a block occupies the position indicated by the tuple

			e.g.
				if (2, 1) is in blocks_list then map_list[2][1] = MapItems.BLOCK

		bombers: a dictionary of dictionaries which contains the starting positions, bomb range and bombs available for both players. 
			use with player_index to find out information about the bomber. 
			
			key: an integer for player_index
			value: {'position': x, y coordinates of the bomber's position, 'bomb_range': bomb range, 'bomb_count': the number of bombs you have available }

			e.g.
				bombers[1]['bomb_range'] will give you the bomb range of a bomb if player 2 is to place a bomb in this turn. 

		player_index: yor player index.
			bombers[player_index][0] returns your starting position

		'''
		self.blocks = blocks_list[:]

	def get_move(self, map_list, bombs, powerups, bombers, explosion_list, player_index, move_number):
		'''
		Called when a move is requested by the game server

		Returns a string which represents the action that the Bomber should carry out in this turn. 
		Defaults to STAY_PUT if a string value that is not associated with a move/bomb move action is passed back. 

		Args: 
			map_list: a list of lists that describes the current map
				map_list[0][0] would return the MapItem occupying position (0, 0)
			
			bombs: a dictionary that contains information of bombs currently on the map. 
				key: a tuple of the bomb's location
				value: a dictionary with keys 'owner', 'range', 'time_left'

				e.g.
					bombs[(13, 5)]['owner'] will return the index of the Bomber who owns the bomb at (13, 5)

				No bombs with time_left = 0 will appear in this list.

			powerups: a dictionary that contains the power-ups currently on the map. 
				key: a tuple of the power-up's location
				value: a string which represents the type of power-up ('FIREUP' or 'BOMBUP').

				e.g.
					if powerups[(2, 3)] == 'FIREUP' then there is a FIREUP in position (2, 3)
			
			bombers: a dictionary that contains the player's current stats. 
				key: player index (0 or 1)
				value: a dictionay with keys 'position', 'bomb_range' and 'bomb_count'

				e.g.
					bombers[0]['bomb_range'] will return player 1's current bomb range. 

			explosion_list: a list of tuples that denotes the position of tiles which are currently exploding.

				By the next get_move call, all currently exploding tiles not be exploding. 
				However, in the next turn, another bomb may cause some of the same tiles to explode. 
			
			player_index: an integer representing your player index.
				bombers[player_index] returns the dictionary containing stats about your bomber
			
			move_number: the current turn number. Use to deterimine if you have missed turns. 
		'''
		stderr.write("\n\n" + str(move_number) + "\n")
		my_position = bombers[player_index]['position']
	
		# updating the list of blocks
		[self.blocks.remove(explosion) for explosion in explosion_list if explosion in self.blocks]

		validmoves = []
		neighbour_blocks = [] 
		
		#how many moves until we dont want to move near a bomb 
		timebomb = 2
		
		#turn making bomb chains on or off. False is off.
		bomb_chain = False
		
		#variable used for jank anti-trapping code, False if safe, True if im gonna move into a bomb
		danger = False

		# find out which directions Bomber can move to.
		for cmove in Directions.values():
			x = my_position[0] + cmove.dx
			y = my_position[1] + cmove.dy

			# Checks to see if neighbours are walkable, and stores the neighbours which are blocks
			if map_list[x][y] in WALKABLE:
				# walkable is a list in enums.py which indicates what type of tiles are walkable
#				exploding = False
				# don't walk into explosions!
#				for explosion in explosion_list:
#					if (x,y) == explosion:
#						exploding = True
#						break
#				if exploding:
				if (x,y) in explosion_list:
					continue
				if not len(bombs):
					validmoves.append((cmove,(x,y)))
#					validmoves.append(cmove)
#					validmoves.append((self.get_value((x,y),map_list,bombs,powerups,not player_index),cmove))
				else:
					bad = False
					for bomb in bombs:
#						dst = self.manhattan_distance(bomb,my_position)
#						stderr.write("There is a bomb at " + str(bomb) + " which is ")
#						stderr.write(str(dst))
#						stderr.write(" away and will explode in ")
#						stderr.write(str(self.get_explode_time(bomb,bombs)) + "\n")
#						stderr.write("this is exploding " + str(explosion_list) + "\n")
						# check if within range of a bomb
						bombrange = bombs[bomb]['range']
						if ((bomb[0] == x) and (abs(bomb[1] - y) <= bombrange)) or ((bomb[1] == y) and (abs(bomb[0] - x) <= bombrange)):
							danger = True
							if timebomb >= self.get_explode_time(bomb,bombs):
								bad = True
								break
					if not bad:
						validmoves.append((cmove,(x,y)))
#						validmoves.append((self.get_value((x,y),map_list,bombs,powerups,not player_index),cmove))
#						validmoves.append(cmove)
			elif (x, y) in self.blocks: 
				neighbour_blocks.append((x, y))


		# can move somewhere, so choose a tile randomly
#		if self.move:
#			stderr.write("Previous move was " + str(self.move) + "\n")
#			stderr.write("Previous move placed a bomb " + str(self.bombMove) + "\n")
#		stderr.write("Valid moves are " + str([str(a) for a in validmoves]) + "\n")

		# there's no where to move to
		if len(validmoves) == 0: 
#			stderr.write("Chose move still\n\n")
			return Directions['still'].action

#	def get_value(self, pos, map_list, bombs, powerups, other_index):
#		self.move = max((self.get_value(move ),move) for move in validmoves)[1]
#		self.move = validmoves[random.randrange(0, len(validmoves))]
#		stderr.write("Chose move " + str(self.move) + "\n")
		
		# if I placed a bomb last move and bomb chaining is off, don't bomb.
		if (bomb_chain == False) and (self.bombMove == True):
			self.bombMove = False
		else:   # place a bomb if there are blocks that can be destroyed
			self.bombMove = len(neighbour_blocks) > 0
			self.move = max((self.get_value(a[1],my_position, map_list,bombs,powerups,not player_index, self.bombMove),a[0]) for a in validmoves)[1]
			
		if self.bombMove and (not danger): 
			return self.move.bombaction
		else: 
			return self.move.action

	def path_exists(self, start, end, map_list):
		''' 
		Takes two tuples that represents the starting, ending point and the currenet map to determine if a path between the two points exists on the map. 

		returns True if there is a path with no blocks, bombs or walls in it's path between start and end. 
		returns False otherwise. 

		Args: 
			start: a tuple which correspond to the starting point of the paths
			end: a tuple which correspond to the ending point of the path.
		'''
		open_list = [start]
		visited = []

		while len(open_list) != 0:
			current = open_list.pop(0)

			for direction in Directions.values():
				x = current[0] + direction.dx
				y = current[1] + direction.dy

				if (x, y) == end: 
					return True

				if (x, y) in visited: 
					continue

				if map_list[x][y] in walkable: 
					open_list.append((x, y))

				visited.append((x, y))

		return False
		
