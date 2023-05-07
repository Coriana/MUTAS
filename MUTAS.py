import sqlite3
import asyncio
import datetime
import telnetlib3
# Import randint from the random module for damage calculation
import random
import json
import re

# SQLite database setup
connection = sqlite3.connect('game_data.db')
cursor = connection.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS rooms
                  (id INTEGER PRIMARY KEY, title TEXT, description TEXT, exits TEXT, npc_ids TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS items
              (id INTEGER PRIMARY KEY, name TEXT, description TEXT, room_id INTEGER, locked INTEGER DEFAULT 0,
              is_edible BOOLEAN, hunger_satiation INTEGER, thirst_satiation INTEGER, spoils BOOLEAN,
              time_created INTEGER, spoiled BOOLEAN, spoiled_time INTEGER, weight INTEGER, rarity INTEGER,
              value INTEGER, max_stack_size INTEGER, equip_slots TEXT, note_id INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS players
                  (id INTEGER PRIMARY KEY, privs INTEGER, name TEXT, room_id INTEGER, hp INTEGER, attack INTEGER,
                  defense INTEGER, online BOOLEAN, hunger INTEGER, thirst INTEGER, strength INTEGER, carry_weight INTEGER,
                  max_carry_weight INTEGER, energy INTEGER, max_energy INTEGER, experience INTEGER, level INTEGER,
                  skill_points INTEGER, abilities TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS equipped_items
                  (id INTEGER PRIMARY KEY, player_id INTEGER, item_id INTEGER, slot TEXT, equipped_time INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS stored_items
                  (id INTEGER PRIMARY KEY, player_id INTEGER, item_id INTEGER, quantity INTEGER, stored_time INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS bank
                  (id INTEGER PRIMARY KEY, player_id INTEGER, gold INTEGER, platinum INTEGER,
                  last_deposit_time INTEGER, last_withdrawal_time INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS item_stats
                  (id INTEGER PRIMARY KEY, item_id INTEGER, stat_type TEXT, stat_description TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS quests
                  (id INTEGER PRIMARY KEY, name TEXT, level_requirement INTEGER, completion_time INTEGER,
                  npc_dialogue TEXT, objective TEXT, progress TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS player_quests
                  (id INTEGER PRIMARY KEY, player_id INTEGER, quest_id INTEGER, start_time INTEGER,
                  completion_time INTEGER, objective_progress TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS npc
                  (id INTEGER PRIMARY KEY, name TEXT, description TEXT, dialogue TEXT, shop_items TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS shops
                  (id INTEGER PRIMARY KEY, shop_name TEXT, shop_description TEXT, shop_items TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS areas
                  (id INTEGER PRIMARY KEY, area_name TEXT, area_description TEXT, music_track TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS monsters
                  (id INTEGER PRIMARY KEY, monster_name TEXT, monster_description TEXT, monster_type TEXT,
                  monster_level INTEGER, hp INTEGER, attack INTEGER, defense INTEGER, speed INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS monster_drops
                  (id INTEGER PRIMARY KEY, monster_id INTEGER, item_id INTEGER, drop_chance INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS player_stats
                  (id INTEGER PRIMARY KEY, player_id INTEGER, stat_name TEXT, stat_value INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS skill_tree
                  (id INTEGER PRIMARY KEY, skill_name TEXT, skill_description TEXT, skill_type TEXT,
                  skill_level INTEGER, skill_cost INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS furniture
                  (id INTEGER PRIMARY KEY, name TEXT, normal_description TEXT, use_description_1p TEXT,
                  use_description_3p TEXT, type TEXT, is_cooking_station BOOLEAN, is_sleeping_furniture BOOLEAN,
                  room_id INTEGER, FOREIGN KEY(room_id) REFERENCES rooms(id));''')
cursor.execute('''CREATE TABLE IF NOT EXISTS notes
                  (id INTEGER PRIMARY KEY, item_id INTEGER, content TEXT, FOREIGN KEY(item_id) REFERENCES items(id))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS room_monsters
                  (id INTEGER PRIMARY KEY, room_id INTEGER, monster_id INTEGER, hp INTEGER,
                  FOREIGN KEY(room_id) REFERENCES rooms(id),
                  FOREIGN KEY(monster_id) REFERENCES monsters(id))''')

# Add default room and items if they don't exist
exits = json.dumps({})
exits1 = json.dumps({"Desolate Plaza": 2})
cursor.execute("INSERT OR IGNORE INTO rooms (id, title, description, exits) VALUES (1, 'Resurrection Chamber', 'This dimly-lit, cavernous space is filled with the hum of ancient machinery that crackles with energy, giving life to the fallen. The walls are lined with moss-covered, flickering monitors displaying cryptic symbols. A large metal door with rusted hinges stands in the middle of the room, leading out to the wasteland.', ?)", (exits1,))
cursor.execute("INSERT OR IGNORE INTO rooms (id, title, description, exits) VALUES (2, 'Desolate Plaza', 'The cracked pavement and overgrown weeds struggle to cover the remains of a once-bustling city square. To the east, the skeletal frame of a ruined skyscraper reaches towards the sky, with a dark entrance beckoning at its base. To the west, the remnants of a small park can be seen, now a tangled mass of mutated flora. A broken road to the north reveals the wreckage of a collapsed bridge, while a pathway to the south leads to the crumbling remains of a once-lavish residential district.', ?)", (exits,))
cursor.execute("INSERT OR IGNORE INTO items (id, name, description, room_id) VALUES (1, 'A wooden staff', 'A sturdy wooden staff with intricate carvings.', 1)")
cursor.execute("INSERT OR IGNORE INTO items (id, name, description, room_id) VALUES (2, 'A small, leather-bound book', 'An old book filled with mysterious symbols.', 1)")
connection.commit()

#defaults
default_hp = 500
default_attack = 100
default_defense = 100

class Event:
    def __init__(self, event_type, **kwargs):
        self.type = event_type
        self.data = kwargs

class EventManager:
    def __init__(self):
        self.listeners = {}

    def register_listener(self, event_type, listener):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)

    def unregister_listener(self, event_type, listener):
        if event_type in self.listeners:
            self.listeners[event_type].remove(listener)

    async def dispatch_event(self, event):
        if event.type in self.listeners:
            for listener in self.listeners[event.type]:
                await listener(event)
                
class CombatManager:
    def __init__(self, event_manager):
        self.event_manager = event_manager
        self.event_manager.register_listener('attack', self.on_attack)

    async def on_attack(self, event):
        attacker_id = event.data['attacker_id']
        target_id = event.data['target_id']
        target_name = event.data['target_name']
        writer = event.data['writer']
        attacker_is_monster = event.data.get('attacker_is_monster', False)
        target_is_monster = event.data.get('target_is_monster', False)
       
        # Your existing combat logic here, for example:
        damage_dealt = await self.combat(attacker_id, target_id, attacker_is_monster, target_is_monster)
        print(f"target_id = {target_id}")
        # Dispatch an event for handling the result of the attack
        attack_result_event = Event('attack_result', attacker_id=attacker_id, target_id=target_id, damage_dealt=damage_dealt, target_is_monster=target_is_monster, target_name=target_name, writer=writer)
        await self.event_manager.dispatch_event(attack_result_event)


    async def combat(self, attacker_id, defender_id, attacker_is_monster=False, target_is_monster=False):
        if attacker_is_monster:
            attacker = cursor.execute("SELECT m.id, rm.hp, m.attack, m.defense FROM room_monsters AS rm JOIN monsters AS m ON rm.monster_id = m.id WHERE rm.monster_id = ?", (attacker_id,)).fetchone()
            attacker_attack_bonus = 0
            attacker_defense_bonus = 0
        else:
            attacker = cursor.execute("SELECT id, hp, attack, defense FROM players WHERE id = ?", (attacker_id,)).fetchone()
            attacker_equipped_items = cursor.execute("SELECT item_id, slot FROM equipped_items WHERE player_id = ?", (attacker_id,)).fetchall()
            attacker_attack_bonus, attacker_defense_bonus = self.calculate_equipped_item_bonuses(attacker_equipped_items)

        if target_is_monster:
            target = cursor.execute("SELECT id, hp, attack, defense FROM monsters WHERE id = ?", (defender_id,)).fetchone()
        else:
            target = cursor.execute("SELECT id, hp, attack, defense FROM players WHERE id = ?", (defender_id,)).fetchone()
        print(attacker[2])
        print(attacker_attack_bonus)
        attacker_attack = attacker[2] + attacker_attack_bonus + random.randint(0, 5)  # Adding randomness to attacker's attack
        print(f"attacker_attack: {attacker_attack}")

        attacker_defense = attacker[3] + attacker_defense_bonus

        target_attack = target[2]
        target_defense = target[3] + random.randint(0, 5)  # Adding randomness to defender's defense
        print(f"defender_defense: {target_defense}")

        damage_dealt = max(attacker_attack - target_defense, 0)
        print(f"damage_dealt: {damage_dealt}")

        return damage_dealt
        
    async def monster_fights_back(self, target_id, player_id, writer):
        while True:
            print(f"{target_id}attacking {player_id}")
            # Check for task cancellation
            if asyncio.current_task().cancelled():
                return
            # Monster fights back
            target_name = cursor.execute("SELECT monster_name FROM monsters WHERE id = ?", (target_id,)).fetchone()[0]
            damage_received = await self.combat(target_id, player_id, target_is_monster=True)
            
            # Fetch player's current HP and update it
            player_hp = cursor.execute("SELECT hp FROM players WHERE id = ?", (player_id,)).fetchone()[0]
            new_player_hp = player_hp - damage_received
            cursor.execute("UPDATE players SET hp = ? WHERE id = ?", (new_player_hp, player_id))
            connection.commit()

            writer.write(f"The {target_name} fights back, dealing {damage_received} damage to you.\r\n".encode())

            # Check if the player is dead
            if new_player_hp <= 0:
                # Handle player death here
                cursor.execute("UPDATE players SET hp = 0 WHERE id = ?", (player_id,))
                connection.commit()
                writer.write(f"The {target_name} has killed you.\r\n".encode())
                break

            # Check if the player wants to flee or exit the combat loop
            # Implement this as per your game mechanics

            # Add a delay before the monster fights back again
            print(f"{target_id} sleeping before attacking {player_id} again")
            await asyncio.sleep(2)  # You can adjust the duration as needed
      

    def damage(self, attacker, defender):
        """Calculate damage dealt during combat."""
        attack = max(attacker[2] - defender[3], 1)
        return randint(1, attack)
        
    def calculate_equipped_item_bonuses(self, equipped_items):
        attack_bonus = 0
        defense_bonus = 0

        for item in equipped_items:
            item_id = item[0]

            # Get the item stats for the equipped item
            item_stats = cursor.execute("SELECT stat_type, stat_value FROM item_stats WHERE item_id = ?", (item_id,)).fetchall()

            # Calculate the attack and defense bonuses for the equipped item
            for stat in item_stats:
                stat_type, stat_value = stat

                if stat_type == "attack":
                    attack_bonus += stat_value
                elif stat_type == "defense":
                    defense_bonus += stat_value

        return attack_bonus, defense_bonus

    async def respawn(self, player_id, player_writer, player_room):
        """Respawn the player in the graveyard."""
        graveyard_id = 2  # Set the room ID of the graveyard
        cursor.execute("UPDATE players SET room_id = ? WHERE id = ?", (graveyard_id, player_id))
        connection.commit()
        player_room = graveyard_id
        player_writer.write("You have died and respawned in the graveyard.\r\n".encode())
        self.show_room(player_writer, player_id)

def clean_input(data):
    lines = [line.decode('utf-8', 'ignore').strip() for line in data.splitlines() if line.strip()]
    print(data)
    return [" ".join(line.split()) for line in lines]

class GameTelnetProtocol:
    # define the calendar constants
    initial_game_year = 8273
    world_start_time = datetime.datetime(2023, 4, 6, 0, 0, 0)
    game_start_time = datetime.datetime.utcnow()
    world_time_elapsed = (game_start_time - world_start_time).total_seconds()
    days_in_month = 15
    months = ['Radiant Dawn', 'Scorching Sun', 'Wasteland Heat', 'Ember Warmth', 'Harvest Ruin', 'Moon\'s Shadow', 'Frostbite', 'Snowbound', 'Chilled Wind', 'Eternal Frost', 'Thawing Spring', 'Rebirth']

    times_of_day = [
    'Haunting Hour', 'Restless Sleep', 'Nightmare', 'Silent Void', 'Faint Glow', 'Bleak Dawn',
    'Sunrise', 'Forgotten Morning', 'Scavenger\'s Meal', 'Early Morning', 'Mid-Morning', 'Late Morning', 'Apex',
    'Early Afternoon', 'Mid-Afternoon', 'Late-Afternoon', 'Fading Light', 'Sunset', 'Twilight',
    'Dusk', 'Shadowfall', 'Moon\'s Embrace', 'Restless Dreams', 'Darkness Descends'
    ]
    writers = {}
    clock_interval = 1
    time_scale_factor = 12 * days_in_month

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.player_id = None
        self.player_name = None
        self.room_id = 1
        self.new_room_name = None
        self.edit_room_name = False
        self.new_item_name = None
        self.edit_furniture_name = None
        self.new_furniture_name  = None
        self.new_description_buffer = []
        self.item_locked = None
        self.current_room_title = ""
        self.clock_task = asyncio.create_task(self.run_clock())
        self.game_time_adjusted = 0
        self.in_combat = False
        self.fight_back_task = None
        self.event_manager = EventManager()
        self.combat_manager = CombatManager(self.event_manager)
        self.event_manager.register_listener('attack_result', self.on_attack_result)

    async def run_clock(self):
        while True:
            game_time = datetime.datetime.utcnow()
            game_time_elapsed = (game_time - self.game_start_time).total_seconds()
            self.game_time_adjusted = self.game_start_time + datetime.timedelta(seconds=(game_time_elapsed + self.world_time_elapsed) * self.time_scale_factor)

            game_year, game_month, game_day, game_time_of_day = self.get_game_date_time()
            #print(f"It is currently {game_time_of_day} on day {game_day} in the month of {game_month}, in the year {game_year}")
            await asyncio.sleep(self.clock_interval)

    def get_game_date_time(self):
        elapsed_time = (self.game_time_adjusted - self.game_start_time).total_seconds()
        elapsed_days = int(elapsed_time // (24 * 3600))

        game_year = elapsed_days // (self.days_in_month * len(self.months)) + self.initial_game_year
        elapsed_days_in_year = elapsed_days % (self.days_in_month * len(self.months))
        game_month = self.months[elapsed_days_in_year // self.days_in_month]
        game_day = elapsed_days_in_year % self.days_in_month + 1

        elapsed_seconds = int(elapsed_time % (24 * 3600))
        game_time_of_day = self.times_of_day[(elapsed_seconds // 3600) % len(self.times_of_day)]

        return game_year, game_month, game_day, game_time_of_day

    async def handle_connection(self):
        self.writer.write("Welcome to the Multi-User Text Adventure System (MUTAS)!\r\n".encode())
        self.writer.write("Please enter your character's name or type 'new' to create a new character:\r\n".encode())
        creating_character = False

        while True:
            data = await self.reader.readline()
            if data:
                line = "".join(clean_input(data)).strip()

                if not self.player_id:
                    if creating_character:
                        cursor.execute("INSERT INTO players (name, room_id, hp, attack, defense, online) VALUES (?, ?, ?, ?, ?, 1)",(line, 1, default_hp, default_attack, default_defense))
                        connection.commit()
                        self.player_id = cursor.lastrowid
                        self.room_id = 1
                        self.player_name = line  # Store player's name in class variable
                        self.writer.write("Character created! Welcome to the game, {}!\n".format(line).encode())
                        self.show_room()
                        await self.notify_entry(self.room_id)  # Notify entry
                        creating_character = False
                    elif line.lower() == "new":
                        self.writer.write("Enter a name for your new character:\n".encode())
                        creating_character = True
                    else:
                        player = cursor.execute("SELECT id, room_id FROM players WHERE name = ?", (line,)).fetchone()
                        if player:
                            self.player_id, self.room_id = player
                            self.player_name = line  # Store player's name in class variable
                            cursor.execute("UPDATE players SET room_id = ?, online = 1 WHERE id = ?", (self.room_id, self.player_id))
                            connection.commit()
                            self.writer.write("Welcome back, {}!\n".format(line).encode())
                            self.show_room()
                            await self.notify_entry(self.room_id)  # Notify entry
                        else:
                            self.writer.write("Character not found. Please try again or type 'new' to create a new character:\n".encode())
                    GameTelnetProtocol.writers[self.player_name] = self.writer  # Use player's name as key
                else:
                    print(f"{self.player_name}: {line}")

                    # Process game commands
                    await self.parse_command(line)  
            else:
                break
        await self.notify_exit(self.room_id)  # Notify exit
        cursor.execute("UPDATE players SET online = 0 WHERE id = ?", (self.player_id,))
        connection.commit()

    async def parse_command(self, line): 
        if self.new_room_name is not None:
            self.new_description_buffer.append(line)
            if not line.strip():  # Blank line received, send buffer to create_new_room()
                description = "".join(self.new_description_buffer).strip()
                await self.create_new_room(description)
                self.new_description_buffer = []  # Reset the buffer
        if self.edit_room_name is not False:
            self.new_description_buffer.append(line)
            if not line.strip():  # Blank line received, send buffer to edit_room()
                description = "\n".join(self.new_description_buffer).strip()
                await self.edit_room(description)
                self.new_description_buffer = []  # Reset the buffer
                self.edit_room_name = False
        if self.new_item_name is not None:
            self.new_description_buffer.append(line)
            if not line.strip():  # Blank line received, send buffer to add_item()
                description = "\n".join(self.new_description_buffer).strip()
                await self.add_item(description)
                self.new_description_buffer = []  # Reset the buffer
        if self.new_furniture_name is not None:
            self.new_description_buffer.append(line)
            if not line.strip():  # Blank line received, send buffer to add_furniture()
                description = "\n".join(self.new_description_buffer).strip()
                await self.add_furniture(self.add_furniture, description, "", "", "furniture")
                self.new_description_buffer = []  # Reset the buffer
                self.new_furniture_name = None
        if self.edit_furniture_name is not None:
            self.new_description_buffer.append(line)
            if not line.strip():  # Blank line received, send buffer to edit_furniture()
                description = "\n".join(self.new_description_buffer).strip()
                await self.edit_furniture(description)
                self.new_description_buffer = []  # Reset the buffer
                self.edit_furniture_name = None
        else:
            command_parts = line.split(" ", 1)
            command = command_parts[0].lower()
            args = None
            if len(command_parts) > 1:
                args = command_parts[1]            # ... other commands


            if command == "go" or command == "/go" :
                if len(command_parts) > 1:
                    if args.isdigit():
                        await self.go_int(args)
                    else:
                        await self.go(args)
                else:
                    self.writer.write("Go where?\r\n".encode())
            elif command == "look":
                self.show_room()
            elif command == "debug_look" or command == "/look":
                self.debug_show_room()
            elif command == "/new_room":
                if len(command_parts) > 1:
                    self.new_room_name = command_parts[1]
                    self.writer.write("Enter a description for the new room '{}':\r\n".format(self.new_room_name).encode())
                else:
                    pass
            elif command == "/new_item":
                if len(command_parts) > 1:
                    self.new_item_name = command_parts[1]
                    self.writer.write("Enter a description for the new item '{}':\r\n".format(self.new_item_name).encode())
                else:
                    pass
            elif command == "/rename_room":
                if len(command_parts) > 1:
                    new_name = command_parts[1]
                    old_name_query = cursor.execute("SELECT title FROM rooms WHERE id = ?", (self.room_id,)).fetchone()
                    if old_name_query is not None:
                        old_name = old_name_query[0]
                        await self.rename_room(old_name, new_name)  # Pass old_name as an argument
                    else:
                        self.writer.write("Error: Room not found.\r\n".encode())
                else:
                    self.writer.write("Please provide a new name for the room.\r\n".encode())
            elif command == "/add_furniture":
                if len(command_parts) > 1:
                    self.new_furniture_name = command_parts[1]
                    self.writer.write("Enter a description for the new furniture '{}':\r\n".format(self.new_furniture_name).encode())
                else:
                    pass
            elif command == "/edit_furniture":
                if len(command_parts) > 1:
                    self.edit_furniture_name = command_parts[1]
                    self.writer.write("Enter a new description for the furniture '{}':\r\n".format(self.edit_furniture_name).encode())
                else:
                    pass
            elif command == "/remove_room":
                if self.room_id == 1:
                    self.writer.write("You cannot remove the starting room.\r\n".encode())
                else:
                    await self.remove_room(self.room_id)

            elif command == "take":
                if len(command_parts) > 1:
                    await self.take_item(command_parts[1])
            elif command == "drop":
                if len(command_parts) > 1:
                    await self.drop_item(command_parts[1])
            elif command == "/edit_room":
                self.edit_room_name = True
                self.writer.write("Enter a new description for the room:\r\n".encode())
            elif command == "say":
                if not args:
                    self.writer.write("Say what?\r\n".encode())
                else:
                    await self.say(args)

            elif command == "/emote":
                if args:
                    await self.emote(args)
                    

            elif command == "add_monster":
                pattern = r'^add_monster\s+(\S+)\s+"([^"]+)"\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)'
                match = re.match(pattern, line)
                if match:
                    monster_name, monster_description, monster_type, monster_level, hp, attack, defense, speed = match.groups()
                    monster_level, hp, attack, defense, speed = int(monster_level), int(hp), int(attack), int(defense), int(speed)
                    cursor.execute("INSERT INTO monsters (monster_name, monster_description, monster_type, monster_level, hp, attack, defense, speed) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (monster_name, monster_description, monster_type, monster_level, hp, attack, defense, speed))
                    connection.commit()
                    self.writer.write(f"Added a new monster: {monster_name}.\r\n".encode())
                else:
                    self.writer.write("Usage: add_monster <monster_name> <monster_description> <monster_type> <monster_level> <hp> <attack> <defense> <speed>\r\n".encode())
                    
            elif command == "read":
                pattern = r'^read\s+(\S+)'
                match = re.match(pattern, line)
                if match:
                    item_name = match.groups()[0]
                    await self.read(item_name)
                else:
                    self.writer.write("Invalid read command. Usage: read <item_name>\r\n".encode())

            elif command == "write_note":
                pattern = r'^write_note\s+(\S+)\s+(.+)'
                match = re.match(pattern, line)
                if match:
                    item_name, content = match.groups()
                    item = cursor.execute("SELECT id FROM items WHERE name = ? AND room_id = ?", (item_name, self.room_id)).fetchone()
                    if not item and self.is_item_in_inventory(item_name):
                        item = cursor.execute("SELECT id FROM items WHERE name = ?", (item_name,)).fetchone()

                    if item:
                        # Replace \n with actual newline character
                        content = content.replace('\\n', '\n')
                        note = cursor.execute("SELECT id FROM notes WHERE item_id = ?", (item[0],)).fetchone()
                        if note:
                            cursor.execute("UPDATE notes SET content = ? WHERE id = ?", (content, note[0]))
                        else:
                            cursor.execute("INSERT INTO notes (item_id, content) VALUES (?, ?)", (item[0], content))
                        connection.commit()
                        self.writer.write(f"You have written on the '{item_name}':\r\n{content}\r\n".encode())
                    else:
                        self.writer.write(f"There is no item with the name '{item_name}' in this room or your inventory.\r\n".encode())
                else:
                    self.writer.write("Invalid write_note command. Usage: write_note <item_name> <content>\r\n".encode())


            elif command == "/spawn_monster":
                if len(command_parts) > 1:
                    monster_name = "".join(args)
                    monster = cursor.execute("SELECT id, monster_name, hp FROM monsters WHERE monster_name = ?", (monster_name,)).fetchone()

                    if monster:
                        monster_id, monster_name, monster_hp = monster
                        cursor.execute("INSERT INTO room_monsters (room_id, monster_id, hp) VALUES (?, ?, ?)", (self.room_id, monster_id, monster_hp))
                        connection.commit()
                        self.writer.write(f"{monster_name} has spawned in the room.\r\n".encode())
                    else:
                        self.writer.write("No such monster found.\r\n".encode())
                else:
                    self.writer.write("Usage: spawn_monster <monster_name>\r\n".encode())


            elif command == "/lock_item":
                self.lock_item(command_parts[1])
            elif command == "/unlock_item":
                self.unlock_item(command_parts[1])
            elif command == "examine":
                if args:
                    await self.examine(args)
                else:
                    self.writer.write("Examine what?\r\n".encode())
            elif command == "/kill":
                if len(command_parts) > 1:
                    monster_name = "".join(args)
                    monster = cursor.execute("SELECT m.id FROM monsters AS m JOIN room_monsters AS rm ON m.id = rm.monster_id WHERE m.monster_name = ? AND rm.room_id = ?", (monster_name, self.room_id)).fetchone()

                    if monster:
                        monster_id = monster[0]
                        cursor.execute("DELETE FROM room_monsters WHERE room_id = ? AND monster_id = ?", (self.room_id, monster_id))
                        connection.commit()
                        self.writer.write(f"{monster_name} has been killed and removed from the room.\r\n".encode())
                    else:
                        self.writer.write("No such monster found in the room.\r\n".encode())
                else:
                    self.writer.write("Usage: kill <monster_name>\r\n".encode())
            elif command == "/heal":
                await self.heal()

            elif command == "attack":
                if len(command_parts) > 1:
                    target_name = "".join(args)
                    target_id, target_is_monster = self.get_target_id(target_name)  # Implement a method to get the target ID based on the target name
                    if target_id:
                       # attack_event = Event('attack', attacker_id=self.player_id, target_id=target_id, target_is_monster=target_is_monster)
                        attack_event = Event('attack', attacker_id=self.player_id, target_id=target_id, writer=self.writer, target_is_monster=target_is_monster, target_name=target_name)

                        await self.event_manager.dispatch_event(attack_event)
                    else:
                        self.writer.write("Unable to attack {}.\r\n".format(target_name).encode())
                else:
                    self.writer.write("Invalid attack command. Please specify a target to attack.\r\n".encode())
                    
            else:
                #self.writer.write("Invalid command.\r\n".encode())
                pass
                
    async def write_note(self, item_name, content):
        # Create a new note in the 'notes' table
        cursor.execute("INSERT INTO notes (content) VALUES (?)", (content,))
        note_id = cursor.lastrowid
        connection.commit()

        # Create a new item in the 'items' table with the note_id
        cursor.execute("INSERT INTO items (name, description, room_id, note_id) VALUES (?, ?, ?, ?)",
                       (item_name, "A note with some writing on it.", self.room_id, note_id))
        connection.commit()

        self.writer.write(f"You have written a note: '{item_name}'.\r\n".encode())

    async def read(self, item_name):
        item = cursor.execute("SELECT id FROM items WHERE name = ? AND room_id = ?", (item_name, self.room_id)).fetchone()
        if not item and self.is_item_in_inventory(item_name):
            item = cursor.execute("SELECT id FROM items WHERE name = ?", (item_name,)).fetchone()

        if item:
            note = cursor.execute("SELECT content FROM notes WHERE item_id = ?", (item[0],)).fetchone()
            if note:
                self.writer.write(f"Reading the '{item_name}':\r\n{note[0]}\r\n".encode())
            else:
                self.writer.write(f"There is nothing written on '{item_name}'.\r\n".encode())
        else:
            self.writer.write(f"There is no item with the name '{item_name}' in this room or your inventory.\r\n".encode())

    def is_item_in_inventory(self, item_name):
        item = cursor.execute("SELECT id FROM items WHERE name = ?", (item_name,)).fetchone()
        if item:
            player_item = cursor.execute("SELECT player_id FROM inventory WHERE item_id = ? AND player_id = ?", (item[0], self.player_id)).fetchone()
            if player_item:
                return True
        return False

            
    async def write_on_item(self, item_name, content):
        # Retrieve the item with the given name
        item = cursor.execute("SELECT id FROM items WHERE name = ? AND (room_id = ? OR id IN (SELECT item_id FROM stored_items WHERE player_id = ?))",
                              (item_name, self.room_id, self.player_id)).fetchone()

        if item:
            item_id = item[0]

            # Create a new note in the 'notes' table
            cursor.execute("INSERT INTO notes (content) VALUES (?)", (content,))
            note_id = cursor.lastrowid
            connection.commit()

            # Update the item with the new note_id
            cursor.execute("UPDATE items SET note_id = ? WHERE id = ?", (note_id, item_id))
            connection.commit()

            self.writer.write(f"You have written on the item: '{item_name}'.\r\n".encode())
        else:
            self.writer.write(f"Item '{item_name}' not found in the room or your inventory.\r\n".encode())
                
    def get_target_id(self, target_name):
        # First, try to find a player target
        print("Debug: target_name:", target_name)
        target = cursor.execute("SELECT id FROM players WHERE name = ? AND room_id = ?", (target_name, self.room_id)).fetchone()
        
        if target:
            print("Debug: target not a monster")
            return target[0], False

        # If the target is not a player, try to find a monster target
        monster_target = cursor.execute("SELECT m.id FROM room_monsters AS rm JOIN monsters AS m ON rm.monster_id = m.id WHERE m.monster_name = ? AND rm.room_id = ?", (target_name, self.room_id)).fetchone()
        
        if monster_target:
            print("Debug: target a monster")
            return monster_target[0], True

        # If no target found, return None
        return None, None
        

    def update_target_hp(self, target_id, damage_dealt, target_is_monster=False):
        if target_is_monster:
            table_name = "room_monsters"
        else:
            table_name = "players"

        # Retrieve the target's current HP
        target_hp = cursor.execute(f"SELECT hp FROM {table_name} WHERE id = ?", (target_id,)).fetchone()

        if target_hp:
            new_hp = target_hp[0] - damage_dealt
            if new_hp < 0:
                new_hp = 0
            
            # Update the target's HP in the database
            cursor.execute(f"UPDATE {table_name} SET hp = ? WHERE id = ?", (new_hp, target_id))
            connection.commit()

            return new_hp

        return None                      

    async def heal(self):
        # Define the amount of HP you want to restore
        hp_to_restore = 20

        # Fetch the player's current HP and maximum HP
        player_hp = cursor.execute("SELECT hp FROM players WHERE id = ?", (self.player_id,)).fetchone()[0]

        # Calculate the new HP after healing
        new_hp = player_hp + hp_to_restore

        # Update the player's HP
        cursor.execute("UPDATE players SET hp = ? WHERE id = ?", (new_hp, self.player_id))
        connection.commit()

        # Notify the player about the healing
        self.writer.write("You have healed for {} HP. Your current HP is {}.\r\n".format(new_hp - player_hp, new_hp).encode())
        
    async def on_attack_result(self, event):
        attacker_id = event.data['attacker_id']
        target_id = event.data['target_id']
        damage_dealt = event.data['damage_dealt']
        target_is_monster = event.data['target_is_monster']
        target_name = event.data['target_name']
        writer = event.data['writer']
        print(f"target_is_monster {target_is_monster}")
        if target_is_monster:
            # Get the monster's current HP and room_id
            room_monster = cursor.execute("SELECT rm.hp, rm.room_id, rm.id FROM room_monsters AS rm WHERE rm.monster_id = ?", (target_id,)).fetchone()

            if room_monster:
                current_hp = room_monster[0]
                room_id = room_monster[1]
                room_monster_id = room_monster[2]  # The ID in the room_monsters table

                new_hp = current_hp - damage_dealt
                print(f"New HP: {new_hp}")  # Debugging
                if new_hp <= 0:
                    # Delete the monster from the room_monsters table
                    cursor.execute("DELETE FROM room_monsters WHERE id = ?", (room_monster_id,))
                    connection.commit()

                    # Send a message to the player that the monster has been defeated
                    writer.write(f"You attacked {target_name} and dealt {damage_dealt} damage. They have died.\r\n".encode())
                    print(f"Monster deleted with room_monster_id: {room_monster_id}")  # Debugging

                    # Cancel the fight back task if it is running
                    if self.fight_back_task and not self.fight_back_task.done():
                        self.fight_back_task.cancel()
                        self.fight_back_task = None  # Set the task to None so that a new task can be created later
                else:
                    # Update the monster's HP in the room_monsters table
                    cursor.execute("UPDATE room_monsters SET hp = ? WHERE id = ?", (new_hp, room_monster_id))
                    connection.commit()
                    print(f"Monster HP updated with room_monster_id: {room_monster_id}, new_hp: {new_hp}")  # Debugging

                    # Send a message to the player about the damage dealt
                    writer.write(f"You attacked {target_name} and dealt {damage_dealt} damage. Their remaining HP is {new_hp}.\r\n".encode())
                    # Create a new fight back task if there is no task or the previous task is done
                    if not self.fight_back_task:
                        self.fight_back_task = asyncio.create_task(self.combat_manager.monster_fights_back(target_id, self.player_id, self.writer))

        else:
            # Update HP, notify players, handle death, and other attack-result related logic here
            new_hp = self.update_target_hp(target_id, damage_dealt, target_is_monster)

            if new_hp is not None:
                if new_hp > 0:
                    self.writer.write("You attacked {} and dealt {} damage. Their remaining HP is {}.\r\n".format(target_name, damage_dealt, new_hp).encode())

                    # Notify the attacked player if the target is not a monster
                    if target_id in GameTelnetProtocol.writers:
                        attacked_player_writer = GameTelnetProtocol.writers[target_id]
                        attacked_player_writer.write("{} attacked you and dealt {} damage. Your remaining HP is {}.\r\n".format(self.player_name, damage_dealt, new_hp).encode())
                    else:
                        pass

                else:
                    self.writer.write("You attacked {} and dealt {} damage. They have died.\r\n".format(target_name, damage_dealt).encode())

                    # Respawn the target player
                    if target_id in GameTelnetProtocol.writers:
                        attacked_player_writer = GameTelnetProtocol.writers[target_id]
                        await self.respawn(target_id, attacked_player_writer)  # Call respawn with the target player's ID


    async def edit_furniture(self, furniture_name):
        furniture = cursor.execute("SELECT id, name, normal_description, use_description_1p, use_description_3p, type, is_cooking_station, is_sleeping_furniture FROM furniture WHERE name = ? AND room_id = ?", (furniture_name, self.room_id)).fetchone()
        if furniture:
            self.writer.write("Enter a new name for the furniture (blank to skip):\r\n".encode())
            name = await self.get_input()
            if name.strip():
                cursor.execute("UPDATE furniture SET name = ? WHERE id = ?", (name, furniture[0]))
                furniture = (furniture[0], name) + furniture[2:]
            self.writer.write("Enter a new normal description for the furniture (blank to skip):\r\n".encode())
            normal_description = await self.get_input()
            if normal_description.strip():
                cursor.execute("UPDATE furniture SET normal_description = ? WHERE id = ?", (normal_description, furniture[0]))
                furniture = furniture[:2] + (normal_description,) + furniture[3:]
            self.writer.write("Enter a new first-person use description for the furniture (blank to skip):\r\n".encode())
            use_description_1p = await self.get_input()
            if use_description_1p.strip():
                cursor.execute("UPDATE furniture SET use_description_1p = ? WHERE id = ?", (use_description_1p, furniture[0]))
                furniture = furniture[:3] + (use_description_1p,) + furniture[4:]
            self.writer.write("Enter a new third-person use description for the furniture (blank to skip):\r\n".encode())
            use_description_3p = await self.get_input()
            if use_description_3p.strip():
                cursor.execute("UPDATE furniture SET use_description_3p = ? WHERE id = ?", (use_description_3p, furniture[0]))
                furniture = furniture[:4] + (use_description_3p,) + furniture[5:]
            self.writer.write("Enter a new type for the furniture (blank to skip):\r\n".encode())
            furniture_type = await self.get_input()
            if furniture_type.strip():
                cursor.execute("UPDATE furniture SET type = ? WHERE id = ?", (furniture_type, furniture[0]))
                furniture = furniture[:5] + (furniture_type,) + furniture[6:]
            self.writer.write("Is the furniture a cooking station (y/n)? (blank to skip):\r\n".encode())
            is_cooking_station = await self.get_input()
            if is_cooking_station.lower() == "y":
                cursor.execute("UPDATE furniture SET is_cooking_station = ? WHERE id = ?", (True, furniture[0]))
                furniture = furniture[:6] + (True,) + furniture[7:]
            elif is_cooking_station.lower() == "n":
                cursor.execute("UPDATE furniture SET is_cooking_station = ? WHERE id = ?", (False, furniture[0]))
                furniture = furniture[:6] + (False,) + furniture[7:]
            self.writer.write("Is the furniture a sleeping furniture (y/n)? (blank to skip):\r\n".encode())
            is_sleeping_furniture = await self.get_input()
            if is_sleeping_furniture.lower() == "y":
                cursor.execute("UPDATE furniture SET is_sleeping_furniture = ? WHERE id = ?", (True, furniture[0]))
                furniture = furniture[:7] + (True,) + furniture[8:]
            elif is_sleeping_furniture.lower() == "n":
                cursor.execute("UPDATE furniture SET is_sleeping_furniture = ? WHERE id = ?", (False, furniture[0]))
                furniture = furniture[:7] + (False,) + furniture[8:]
                
    async def get_input(self):
        while True:
            line = await self.reader.readline()
            if not line:
                break
            line = line.decode().strip()
            return line

    async def examine(self, target_name):
        # Check if target is an item in the room
        item = cursor.execute("SELECT * FROM items WHERE name = ? AND room_id = ?", (target_name, self.room_id)).fetchone()
        if item:
            item_stats = cursor.execute("SELECT * FROM item_stats WHERE item_id = ?", (item[0],)).fetchall()
            stats = "\n".join(["{}: {}".format(s[2], s[3]) for s in item_stats])
            examine_message = "Item: {}\nDescription: {}".format(item[1], item[2])
            if stats:
                examine_message += "\nStats:\n{}".format(stats)
            self.writer.write((examine_message + "\r\n").encode())
            return
        # Check if target is a furniture in the room
        furniture = cursor.execute("SELECT * FROM furniture WHERE name = ? AND room_id = ?", (target_name, self.room_id)).fetchone()
        if furniture:
            examine_message = "Furniture: {}\nDescription: {}\nType: {}".format(furniture[1], furniture[2], furniture[5])
            self.writer.write((examine_message + "\r\n").encode())
            return

        # Check if target is a player in the room
        player = cursor.execute("SELECT * FROM players WHERE name = ? AND room_id = ?", (target_name, self.room_id)).fetchone()
        if player:
            equipped_items = cursor.execute("SELECT * FROM equipped_items WHERE player_id = ?", (player[0],)).fetchall()
            equipped_item_names = [cursor.execute("SELECT name FROM items WHERE id = ?", (i[2],)).fetchone()[0] for i in equipped_items]
            equipment = "\n".join(["{}: {}".format(i[3], n) for i, n in zip(equipped_items, equipped_item_names)])
            player_stats = cursor.execute("SELECT * FROM player_stats WHERE player_id = ?", (player[0],)).fetchall()
            stats = "\n".join(["{}: {}".format(s[2], s[3]) for s in player_stats])
            examine_message = "Player: {}\nHP: {}\nAttack: {}\nDefense: {}\nEquipment:\n{}\nStats:\n{}".format(player[2], player[4], player[5], player[6], equipment, stats)
            self.writer.write((examine_message + "\r\n").encode())
            return

        # Check if target is an NPC in the room
        npc = cursor.execute("SELECT * FROM npc WHERE name = ? AND id IN (SELECT npc_id FROM rooms WHERE id = ?)", (target_name, self.room_id)).fetchone()
        if npc:
            examine_message = "NPC: {}\nDescription: {}\nDialogue: {}".format(npc[1], npc[2], npc[3])
            self.writer.write((examine_message + "\r\n").encode())
            return

        self.writer.write("Cannot find '{}' in this room.\r\n".encode(target_name))
        
    async def add_furniture(self, name, normal_description, use_description_1p, use_description_3p, furniture_type):
        print(name)
        self.writer.write("Is the furniture a cooking station (y/n)? (blank to skip):\r\n".encode())
        is_cooking_station = await self.get_input()
        if is_cooking_station.lower() == "y":
            is_cooking_station = True
        elif is_cooking_station.lower() == "n" or not is_cooking_station:
            is_cooking_station = False
        self.writer.write("Is the furniture a sleeping furniture (y/n)? (blank to skip):\r\n".encode())
        is_sleeping_furniture = await self.get_input()
        if is_sleeping_furniture.lower() == "y":
            is_sleeping_furniture = True
        elif is_sleeping_furniture.lower() == "n" or not is_sleeping_furniture:
            is_sleeping_furniture = False
        cursor.execute("INSERT INTO furniture (name, normal_description, use_description_1p, use_description_3p, type, is_cooking_station, is_sleeping_furniture, room_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (self.new_furniture_name, normal_description, use_description_1p, use_description_3p, furniture_type, is_cooking_station, is_sleeping_furniture, self.room_id))
        connection.commit()
        self.writer.write("New furniture '{}' added to the current room.\r\n".format(self.new_furniture_name).encode())

    async def say(self, message):
        player_name = cursor.execute("SELECT name FROM players WHERE id = ?", (self.player_id,)).fetchone()[0]
        players = cursor.execute("SELECT id FROM players WHERE room_id = ? AND id != ?", (self.room_id, self.player_id)).fetchall()
        print(f"{player_name} says '{message}' to players: {players}")
        for player_id, in players:
            print(f"sending to {player_id} pt 1")

            if player_id in GameTelnetProtocol.writers:
                print(f"sending to {player_id} pt 2")
                writer = GameTelnetProtocol.writers[player_id]
                writer.write("{} says: {}\r\n".format(player_name, message).encode())
        self.writer.write("You say: {}\r\n".format(message).encode())
        
    async def emote(self, message):
        player_name = cursor.execute("SELECT name FROM players WHERE id = ?", (self.player_id,)).fetchone()[0]
        players = cursor.execute("SELECT id FROM players WHERE room_id = ? AND id != ?", (self.room_id, self.player_id)).fetchall()
        print(f"{player_name} '{message}' to players: {players}")
        for player_id, in players:
            print(f"sending to {player_id} pt 1")

            if player_id in GameTelnetProtocol.writers:
                print(f"sending to {player_id} pt 2")
                writer = GameTelnetProtocol.writers[player_id]
                writer.write("{} {}\r\n".format(player_name, message).encode())
        self.writer.write("You {}\r\n".format(message).encode())
        
    async def add_item(self, description):
        cursor.execute("INSERT INTO items (name, description, room_id) VALUES (?, ?, ?)", (self.new_item_name, description, self.room_id))
        connection.commit()
        self.writer.write("New item '{}' added to the current room.\r\n".format(self.new_item_name).encode())
        self.new_item_name = None
        
    async def edit_room(self, new_description):
        if not new_description:
            self.writer.write("Please provide a new description for the room.\r\n".encode())
            return

        # Update the room description in the database
        cursor.execute("UPDATE rooms SET description = ? WHERE id = ?", (new_description, self.room_id))
        connection.commit()

        self.writer.write("Room description updated successfully.\r\n".encode())
        self.show_room()
        
    async def rename_room(self, old_name, new_name):
        if not new_name:
            self.writer.write("Please provide a new name for the room.\r\n".encode())
            return

        # Get the room ID of the old room
        old_room_id = cursor.execute("SELECT id FROM rooms WHERE title = ?", (old_name,)).fetchone()[0]

        # Update the room name in the database
        print(f"{self.room_id} being updated from {old_name} to {new_name}")
        cursor.execute("UPDATE rooms SET title = ? WHERE id = ?", (new_name, self.room_id))
        connection.commit()
        cursor.execute(
            "UPDATE rooms SET exits = json_set(exits, ?, ?) WHERE json_extract(exits, ?) IS NOT NULL",
            ("$." + new_name.lower(), old_room_id, "$." + old_name.lower())
        )
        connection.commit()

        self.writer.write("Room name updated successfully.\r\n".encode())
        self.show_room()

        # Update the exit names
        await self.update_exits(old_name, new_name, old_room_id)

    async def update_exits(self, old_name, new_name, old_room_id):
        # Get all rooms connected to the old room
        connected_rooms = cursor.execute(
            "SELECT id, exits FROM rooms WHERE json_extract(exits, ?) IS NOT NULL",
            ("$." + str(old_room_id),)
        ).fetchall()

        for room_id, exits_json in connected_rooms:
            exits = json.loads(exits_json)
            if str(old_room_id) in exits:
                # Update the exit name and ID
                exits[new_name.lower()] = exits.pop(str(old_room_id))

                # Update the database with the new exit information
                cursor.execute("UPDATE rooms SET exits = ? WHERE id = ?", (json.dumps(exits), room_id))
                connection.commit()
                
    async def remove_room(self, room_id):
        # Get the room information and exits
        room_info = cursor.execute("SELECT title, exits FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if not room_info:
            self.writer.write("Error: Room not found.\r\n".encode())
            return
        room_name, exits = room_info
        
        # Remove the room from the database
        cursor.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
        connection.commit()
        
        # Update the exits of connected rooms
        connected_rooms = json.loads(exits)
        for exit_name, connected_room_id in connected_rooms.items():
            connected_exits = json.loads(cursor.execute("SELECT exits FROM rooms WHERE id = ?", (connected_room_id,)).fetchone()[0])
            # Find the correct key (room ID) to delete the exit
            key_to_delete = None
            for key, value in connected_exits.items():
                if value == room_id:
                    key_to_delete = key
                    break
        
            if key_to_delete is not None:
                del connected_exits[key_to_delete]
                cursor.execute("UPDATE rooms SET exits = ? WHERE id = ?", (json.dumps(connected_exits), connected_room_id))
                connection.commit()
        
        self.writer.write("The room '{}' has been removed.\r\n".format(room_name).encode())
        
        # Move the player back to the starting room
        cursor.execute("UPDATE players SET room_id = ? WHERE id = ?", (1, self.player_id))
        connection.commit()
        self.room_id = 1
        notify_entry(1)
        self.show_room()

    def check_admin_privileges(self):
        admin = cursor.execute("SELECT is_admin FROM players WHERE id = ?", (self.player_id,)).fetchone()
        return admin[0] == 1

    async def go_int(self, exit_input):
        if not exit_input:
            self.writer.write("Go where?\r\n".encode())
            return

        room = cursor.execute("SELECT exits FROM rooms WHERE id = ?", (self.room_id,)).fetchone()

        exit_number = None
        if exit_input.isdigit():
            exit_number = int(exit_input)
        if room:
            exits = json.loads(room[0])
            exit_names = list(exits.keys())
            if 0 < exit_number <= len(exits):
                exit_name = list(exits.keys())[exit_number - 1]
            else:
                self.writer.write("Invalid exit number.\r\n".encode())
                return

            await self.handle_exit(exit_name)

        else:
            self.writer.write("Error: Room not found.\r\n".encode())

    async def go(self, exit_input):
        if not exit_input:
            self.writer.write("Go where?\r\n".encode())
            return

        room = cursor.execute("SELECT exits FROM rooms WHERE id = ?", (self.room_id,)).fetchone()
        if room:
            exits = json.loads(room[0])
            if exit_input.lower() in exits:
                await self.handle_exit(exit_input.lower())
            else:
                self.writer.write("There's no exit called '{}'.\r\n".format(exit_input.capitalize()).encode())
        else:
            self.writer.write("Error: Room not found.\r\n".encode())

    async def handle_exit(self, exit_name):
        room = cursor.execute("SELECT exits FROM rooms WHERE id = ?", (self.room_id,)).fetchone()
        exits = json.loads(room[0])

        new_room_id = exits[exit_name]

        # Notify players in the current room that the player is leaving
        player_name = cursor.execute("SELECT name FROM players WHERE id = ?", (self.player_id,)).fetchone()[0]
        await self.notify_room(self.room_id, "{} has left through the exit '{}'.\r\n".format(player_name, exit_name))

        # Update player's room_id
        cursor.execute("UPDATE players SET room_id = ? WHERE id = ?", (new_room_id, self.player_id))
        connection.commit()

        self.room_id = new_room_id
        self.show_room()

        # Notify players in the new room that the player has entered
        await self.notify_entry(new_room_id)

    async def create_new_room(self, description):
        exits = json.dumps({})  # Empty dictionary for exits
        cursor.execute("INSERT INTO rooms (title, description, exits) VALUES (?, ?, ?)", (self.new_room_name, description, exits))
        connection.commit()
        new_room_id = cursor.lastrowid

        # Link the new room to the current room
        current_exits = json.loads(cursor.execute("SELECT exits FROM rooms WHERE id = ?", (self.room_id,)).fetchone()[0])
        current_exits[self.new_room_name] = new_room_id
        cursor.execute("UPDATE rooms SET exits = ? WHERE id = ?", (json.dumps(current_exits), self.room_id))
        connection.commit()
        # Link the current room to the new room
        new_exits = {self.current_room_title: self.room_id}
        cursor.execute("UPDATE rooms SET exits = ? WHERE id = ?", (json.dumps(new_exits), new_room_id))
        connection.commit()

        self.writer.write("New room '{}' created and connected to the current room.\r\n".format(self.new_room_name).encode())

        self.new_room_name = None
        self.debug_show_room

    async def notify_room(self, room_id, message):
        players = cursor.execute("SELECT id FROM players WHERE room_id = ? AND id != ?", (room_id, self.player_id)).fetchall()
        for player_id, in players:
            if player_id in GameTelnetProtocol.writers:
                writer = GameTelnetProtocol.writers[player_id]
                writer.write(message.encode())
        await asyncio.sleep(0)

    async def notify_entry(self, room_id):
        player_name = cursor.execute("SELECT name FROM players WHERE id = ?", (self.player_id,)).fetchone()[0]
        await self.notify_room(room_id, "{} has entered the room.\r\n".format(player_name))

    async def notify_exit(self, room_id):
        player_name = cursor.execute("SELECT name FROM players WHERE id = ?", (self.player_id,)).fetchone()[0]
        await self.notify_room(room_id, "{} has left the room.\r\n".format(player_name))

    async def take_item(self, item_name):
        item = cursor.execute("SELECT id, locked FROM items WHERE name = ? AND room_id = ?", (item_name, self.room_id)).fetchone()
        if item:
            if not item[1]:
                cursor.execute("UPDATE items SET room_id = NULL WHERE id = ?", (item[0],))
                connection.commit()
                self.writer.write("You have taken the item '{}'.\r\n".format(item_name).encode())
                player_name = cursor.execute("SELECT name FROM players WHERE id = ?", (self.player_id,)).fetchone()[0]
                await self.notify_room(self.room_id, "{} has taken the item '{}'.\r\n".format(player_name, item_name))
            else:
                self.writer.write("The item '{}' is locked and cannot be taken.\r\n".format(item_name).encode())
        else:
            self.writer.write("Item '{}' not found in this room.\r\n".format(item_name).encode())

    async def drop_item(self, item_name):
        item = cursor.execute("SELECT id, room_id FROM items WHERE name = ? AND room_id IS NULL", (item_name,)).fetchone()
        if item:
            cursor.execute("UPDATE items SET room_id = ? WHERE id = ?", (self.room_id, item[0]))
            connection.commit()
            self.writer.write("You have dropped the item '{}'.\r\n".format(item_name).encode())
            player_name = cursor.execute("SELECT name FROM players WHERE id = ?", (self.player_id,)).fetchone()[0]
            await self.notify_room(self.room_id, "{} has dropped the item '{}'.\r\n".format(player_name, item_name))
        else:
            self.writer.write("You don't have the item '{}'.\r\n".format(item_name).encode())
            
    def unlock_item(self, item_name):
        item = cursor.execute("SELECT id, room_id, locked FROM items WHERE name = ? AND room_id = ?", (item_name, self.room_id)).fetchone()
        if item:
            if item[2]:
                cursor.execute("UPDATE items SET locked = 0 WHERE id = ?", (item[0],))
                connection.commit()
                self.item_locked = None
                self.writer.write("The item '{}' has been unlocked.\r\n".format(item_name).encode())
            else:
                self.writer.write("The item '{}' is not locked and cannot be unlocked.\r\n".format(item_name).encode())
        else:
            self.writer.write("Item '{}' not found in this room.\r\n".format(item_name).encode())

    def lock_item(self, item_name):
        item = cursor.execute("SELECT id, room_id, locked FROM items WHERE name = ? AND room_id = ?", (item_name, self.room_id)).fetchone()
        if item:
            if not item[2]:
                cursor.execute("UPDATE items SET locked = 1 WHERE id = ?", (item[0],))
                connection.commit()
                self.item_locked = item_name
                self.writer.write("The item '{}' has been locked in place.\r\n".format(item_name).encode())
            else:
                self.writer.write("The item '{}' is already locked in place.\r\n".format(item_name).encode())
        else:
            self.writer.write("Item '{}' not found in this room.\r\n".format(item_name).encode())
        
    def connection_made(self, transport):
        self.transport = transport
        # Prompt player to log in or create a new character
        transport.write("Welcome to the Multi-User Text Adventure System (MUTAS)!\r\n".encode())
        transport.write("Please enter your character's name or type 'new' to create a new character:\r\n".encode())

    def connection_lost(self, exc):
        # Set player as offline when they disconnect
        print(f"Player {exc} left the game.")
        if self.player_id:
            cursor.execute("UPDATE players SET online = 0 WHERE id = ?", (self.player_id,))
            connection.commit()
            
    def show_room(self, player_writer=None, target_player_id=None):
        if player_writer is None:
            player_writer = self.writer

        if target_player_id is None:
            target_player_id = self.player_id

        room_id_query = cursor.execute("SELECT room_id FROM players WHERE id = ?", (target_player_id,)).fetchone()
        if room_id_query:
            target_room_id = room_id_query[0]
        else:
            target_room_id = self.room_id

        room = cursor.execute("SELECT title, description, exits FROM rooms WHERE id = ?", (target_room_id,)).fetchone()
        if room:
            title, description, exits = room
            self.current_room_title = title
            player_writer.write("= {} =\r\n".format(title).encode())
            player_writer.write("{}\r\n".format(description).encode())

            # get the current in-game date and time
            game_year, game_month, game_day, game_time_of_day = self.get_game_date_time()
            # send the date and time to the client
            player_writer.write(f"\nIt is currently {game_time_of_day} on day {game_day} in the month of {game_month}, in the year {game_year}\r\n".encode())
            
            # Show items in the room
            items = cursor.execute("SELECT name FROM items WHERE room_id = ? AND locked = 0", (target_room_id,)).fetchall()
            if items:
                player_writer.write("\r\nItems:\r\n".encode())
                for item in items:
                    player_writer.write("- {}\r\n".format(item[0]).encode())

            # Show players in the room
            players = cursor.execute("SELECT name FROM players WHERE room_id = ? AND id != ? AND online = 1", (target_room_id, target_player_id)).fetchall()
            if players:
                player_writer.write("\r\nPlayers:\r\n".encode())
                for player in players:
                    player_writer.write("- {} (online)\r\n".format(player[0]).encode())
                    
            # Show monsters in the room
            monsters = cursor.execute("SELECT rm.id, m.monster_name FROM room_monsters AS rm JOIN monsters AS m ON rm.monster_id = m.id WHERE rm.room_id = ?", (target_room_id,)).fetchall()
            if monsters:
                player_writer.write("\r\nMonsters:\r\n".encode())
                for monster in monsters:
                    player_writer.write("- {}\r\n".format(monster[1]).encode())

            player_writer.write("\nExits:\r\n".encode())
            exits = json.loads(exits)
            for i, (exit_name, room_id) in enumerate(exits.items()):
                if room_id != 0:
                    room_name = cursor.execute("SELECT title FROM rooms WHERE id = ?", (room_id,)).fetchone()[0]
                    player_writer.write("- {}:{}\r\n".format(i + 1, exit_name).encode())
            
        else:
            player_writer.write("Error: Room not found.\r\n".encode())
            player_writer.write("Moving back to safe room.\r\n".encode())
            # Move the player back to the starting room
            cursor.execute("UPDATE players SET room_id = ? WHERE id = ?", (1, target_player_id))
            connection.commit()
            self.room_id = 1
            self.show_room()
            
    def debug_show_room(self, player_writer=None, target_player_id=None):
        if player_writer is None:
            player_writer = self.writer

        if target_player_id is None:
            target_player_id = self.player_id

        room_id_query = cursor.execute("SELECT room_id FROM players WHERE id = ?", (target_player_id,)).fetchone()
        if room_id_query:
            target_room_id = room_id_query[0]
        else:
            target_room_id = self.room_id

        room = cursor.execute("SELECT title, description, exits FROM rooms WHERE id = ?", (target_room_id,)).fetchone()
        if room:
            title, description, exits = room
            self.current_room_title = title
            player_writer.write("= {} =\r\n".format(title).encode())
            player_writer.write("{}\r\n".format(description).encode())

            # get the current in-game date and time
            #game_year, game_month, game_day, game_time_of_day = self.get_game_date_time()
            # send the date and time to the client
            #player_writer.write(f"\nIt is currently {game_time_of_day} on day {game_day} in the month of {game_month}, in the year {game_year}\r\n".encode())
            

            # Show furniture and locked items in the room
            furniture = cursor.execute("SELECT name FROM furniture WHERE room_id = ?", (target_room_id,)).fetchall()
            locked_items = cursor.execute("SELECT name FROM items WHERE room_id = ? AND locked = 1", (target_room_id,)).fetchall()
            if furniture or locked_items:
                player_writer.write("\r\nOther items:\r\n".encode())
                for furniture in furniture:
                    player_writer.write("- {}\r\n".format(furniture[0]).encode())
                for li in locked_items:
                    player_writer.write("- {}\r\n".format(li[0]).encode())
                
            # Show items in the room
            items = cursor.execute("SELECT name FROM items WHERE room_id = ? AND locked = 0", (target_room_id,)).fetchall()
            if items:
                player_writer.write("\r\nItems:\r\n".encode())
                for item in items:
                    player_writer.write("- {}\r\n".format(item[0]).encode())

            # Show players in the room
            players = cursor.execute("SELECT name FROM players WHERE room_id = ? AND id != ? AND online = 1", (target_room_id, target_player_id)).fetchall()
            if players:
                player_writer.write("\r\nPlayers:\r\n".encode())
                for player in players:
                    player_writer.write("- {} (online)\r\n".format(player[0]).encode())
                    
            # Show monsters in the room
            monsters = cursor.execute("SELECT rm.id, m.monster_name FROM room_monsters AS rm JOIN monsters AS m ON rm.monster_id = m.id WHERE rm.room_id = ?", (target_room_id,)).fetchall()
            if monsters:
                player_writer.write("\r\nMonsters:\r\n".encode())
                for monster in monsters:
                    player_writer.write("- {} (ID: {})\r\n".format(monster[1], monster[0]).encode())

            player_writer.write("\nExits:\r\n".encode())
            exits = json.loads(exits)
            for i, (exit_name, room_id) in enumerate(exits.items()):
                if room_id != 0:
                    room_name = cursor.execute("SELECT title FROM rooms WHERE id = ?", (room_id,)).fetchone()[0]
                    player_writer.write("- {}:{}\r\n".format(i + 1, exit_name).encode())
            
        else:
            player_writer.write("Error: Room not found.\r\n".encode())
            player_writer.write("Moving back to safe room.\r\n".encode())
            # Move the player back to the starting room
            cursor.execute("UPDATE players SET room_id = ? WHERE id = ?", (1, target_player_id))
            connection.commit()
            self.room_id = 1
            self.show_room()
        
# Start the telnet server
async def main():
    async def handle_client(reader, writer):
        protocol = GameTelnetProtocol(reader, writer)
        await protocol.handle_connection()
        writer.close()

    server = await asyncio.start_server(handle_client, '0.0.0.0', 23)
    cursor.execute("UPDATE players SET online = 0")
    connection.commit()
    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
connection.close()