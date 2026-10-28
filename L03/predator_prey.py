import mesa
from mesa.visualization import SolaraViz, make_space_component, make_plot_component
from mesa.datacollection import DataCollector
from mesa.space import PropertyLayer
import solara as sl
import numpy as np

GRID_SIZE = 16
NUM_SHEEP = 20
NUM_WOLVES = 10
NUM_GRASS = 20
NUM_STEPS_UNTIL_SHEEP_BREEDS = 3
NUM_STEPS_UNTIL_SHEEP_STARVES = 5
NUM_STEPS_UNTIL_WOLF_BREEDS = 5
NUM_STEPS_UNTIL_WOLF_STARVES = 5
NUM_STEPS_UNTIL_GRASS_GROWS = 5
NUM_STEPS_UNTIL_GRASS_REGENERATES = 10

class GrassAgent(mesa.Agent):
    def __init__(self, model, steps_until_grass_grows = NUM_STEPS_UNTIL_GRASS_GROWS, steps_until_regenerates = NUM_STEPS_UNTIL_GRASS_REGENERATES):
        super().__init__(model)
        self.type = 'grass'
        self.steps_until_grows = steps_until_grass_grows
        self.steps_until_regenerates = steps_until_regenerates
        self.isAvailable = True

    def step(self):
        self.steps_until_grows -= 1

        if self.steps_until_grows <= 0:
            self.breed()
            self.steps_until_grows = NUM_STEPS_UNTIL_GRASS_GROWS

        self.steps_until_regenerates -= 1
        if self.steps_until_regenerates <= 0 and self.isAvailable == False:
            self.steps_until_regenerates = NUM_STEPS_UNTIL_GRASS_REGENERATES
            self.isAvailable = True
    
    def breed(self):
        # generate another grass agent in an empty space
        neighbor_pos = self.model.grid.get_neighborhood(self.pos, 
                                                        moore = False,
                                                        include_center = False, 
                                                        radius = 1)
        valid_pos = []
        for p in neighbor_pos:
            neighbor_agents = self.model.grid.get_cell_list_contents(p)
            if not neighbor_agents:
                # empty_cell
                valid_pos.append(p)

        if valid_pos:
            new_pos = self.random.choice(valid_pos)
            self.model.spawn_grass(new_pos)

    def remove(self):
        # if self.pos is not None:
        #     self.model.grid.remove_agent(self)
        # super().remove()
        self.isAvailable = False


class SheepAgent(mesa.Agent):
    def __init__(self, model, steps_until_starve = NUM_STEPS_UNTIL_SHEEP_STARVES, steps_until_breed = NUM_STEPS_UNTIL_SHEEP_BREEDS):
        super().__init__(model)
        self.type = 'sheep'
        self.steps_until_breed = steps_until_breed
        self.steps_until_starve = steps_until_starve
        self.eat = False
        
    def step(self):

        self.steps_until_starve -= 1

        if self.steps_until_starve <= 0:
            self.remove()
            return

        self.move_eat()
        self.steps_until_breed -= 1

        if self.steps_until_breed <= 0 and self.eat == True:
            self.breed()
            self.steps_until_breed = NUM_STEPS_UNTIL_SHEEP_BREEDS

    def breed(self):
        # generate another sheep agent in an empty space
        neighbor_pos = self.model.grid.get_neighborhood(self.pos, 
                                                        moore = False, # no diagonals
                                                        include_center = False, 
                                                        radius = 1)
        valid_pos = []
        for p in neighbor_pos:
            neighbor_agents = self.model.grid.get_cell_list_contents(p)
            neighbor_agents = [neighbor for neighbor in neighbor_agents if neighbor.type not in ['wolf', 'sheep']]
            if not neighbor_agents:
                # empty_cell
                valid_pos.append(p)

            for _ in neighbor_agents:
                valid_pos.append(p)

        if valid_pos:
            new_pos = self.random.choice(valid_pos)
            self.model.spawn_sheep(new_pos)
        self.eat = False

    def move(self):
        # move to empty space
        neighbor_pos = self.model.grid.get_neighborhood(self.pos, 
                                                        moore = False, # no diagonals
                                                        include_center = False, 
                                                        radius = 1)
        # avoid collisions with other sheep/wolves
        valid_pos = []
        for p in neighbor_pos:
            neighbor_agents = self.model.grid.get_cell_list_contents(p)
            if not neighbor_agents:
                #empty cell
                valid_pos.append(p)

        if valid_pos:
            new_pos = self.random.choice(valid_pos)
            self.model.grid.move_agent(self, new_pos)

    def move_eat(self):
        # try to find prey in immediate neighborhood, 
        # otherwise move to unoccupied cell

        neighbor_pos = self.model.grid.get_neighborhood(self.pos, 
                                                        moore = False, # no diagonals
                                                        include_center = False,
                                                        radius = 1)
        # try to find a sheep to eat
        valid_pos = []
        food_agent = None
        for p in neighbor_pos:
            neighbor_agents = self.model.grid.get_cell_list_contents(p)
            neighbor_agents = [neighbor for neighbor in neighbor_agents if neighbor.type not in ['wolf', 'sheep']]
            if not neighbor_agents:
                # empty position
                valid_pos.append(p)
            else:
                for neighbor in neighbor_agents:
                    if neighbor.type == 'grass' and neighbor.isAvailable == True:
                        food_agent = neighbor
                        break # found food
                if food_agent:
                    break
            
        if food_agent:
            # move to the prey's position and eat it
            new_pos = food_agent.pos
            self.model.grid.move_agent(self, new_pos)
            food_agent.remove()
            self.steps_until_starve = NUM_STEPS_UNTIL_SHEEP_STARVES
            self.eat = True
        else:
            if valid_pos:
                # move randomly in a free position
                new_pos = self.random.choice(valid_pos)
                self.model.grid.move_agent(self, new_pos)

    def remove(self):
        if self.pos is not None:
            self.model.grid.remove_agent(self)
        super().remove()

class WolfAgent(mesa.Agent):
    def __init__(self, model, steps_until_breed = NUM_STEPS_UNTIL_WOLF_BREEDS, steps_until_starve = NUM_STEPS_UNTIL_WOLF_STARVES):
        super().__init__(model)
        self.type = 'wolf'
        self.steps_until_breed = steps_until_breed
        self.steps_until_starve = steps_until_starve
        self.eat = False

    def step(self):
        self.steps_until_starve -= 1

        if self.steps_until_starve <= 0:
            self.remove()
            return

        self.steps_until_breed -= 1

        if self.steps_until_breed <= 0 and self.eat == True:
            self.breed()
            self.steps_until_breed = NUM_STEPS_UNTIL_WOLF_BREEDS

        self.move_eat()

    def move_eat(self):
        # try to find prey in immediate neighborhood, 
        # otherwise move to unoccupied cell
        neighbor_pos = self.model.grid.get_neighborhood(self.pos, 
                                                        moore = False, # no diagonals
                                                        include_center = False,
                                                        radius = 1)
        # try to find a sheep to eat
        valid_pos = []
        food_agent = None
        for p in neighbor_pos:
            neighbor_agents = self.model.grid.get_cell_list_contents(p)
            if not neighbor_agents:
                # empty position
                valid_pos.append(p)
            else:
                for neighbor in neighbor_agents:
                    if neighbor.type == 'sheep':
                        food_agent = neighbor
                        break # found food
                    elif neighbor.type == 'grass':
                        valid_pos.append(neighbor.pos)
                if food_agent:
                    break;

        if food_agent:
            # move to the prey's position and eat it
            new_pos = food_agent.pos
            self.model.grid.move_agent(self, new_pos)
            food_agent.remove()
            self.eat = True
            self.steps_until_starve = NUM_STEPS_UNTIL_WOLF_STARVES
        else:
            if valid_pos:
                # move randomly in a free position
                new_pos = self.random.choice(valid_pos)
                self.model.grid.move_agent(self, new_pos)

    def breed(self):
        # generate another wolf agent in an empty space
        neighbor_pos = self.model.grid.get_neighborhood(self.pos, 
                                                        moore = False, # no diagonals
                                                        include_center = False, 
                                                        radius = 1)
        valid_pos = []
        for p in neighbor_pos:
            neighbor_agents = self.model.grid.get_cell_list_contents(p)
            if not neighbor_agents:
                # empty_cell
                valid_pos.append(p)
            
            for neighbor in neighbor_agents:
                if neighbor.type == 'grass':
                    valid_pos.append(p)
    
        if valid_pos:
            new_pos = self.random.choice(valid_pos)
            self.model.spawn_wolf(new_pos)
        self.eat = False

    def remove(self):
        if self.pos is not None:
            self.model.grid.remove_agent(self)
        super().remove()

class PredatorPreyModel(mesa.Model):
    def __init__(self, 
                 grid_size = GRID_SIZE,
                 num_sheep = NUM_SHEEP,
                 num_wolves = NUM_WOLVES,
                 num_grass = NUM_GRASS,
                 num_steps_until_sheep_breeds = NUM_STEPS_UNTIL_SHEEP_BREEDS,
                 num_steps_until_wolf_breeds = NUM_STEPS_UNTIL_WOLF_BREEDS,
                 num_steps_until_wolf_starves = NUM_STEPS_UNTIL_WOLF_STARVES,
                 num_steps_until_grass_grows = NUM_STEPS_UNTIL_GRASS_GROWS,
                 num_steps_until_sheep_starves = NUM_STEPS_UNTIL_SHEEP_STARVES,
                 num_steps_until_grass_regenerates = NUM_STEPS_UNTIL_GRASS_REGENERATES
                 ):
        super().__init__()

        self.num_steps_until_sheep_starves = num_steps_until_sheep_starves
        self.num_steps_until_sheep_breeds = num_steps_until_sheep_breeds
        self.num_steps_until_wolf_breeds = num_steps_until_wolf_breeds
        self.num_steps_until_wolf_starves = num_steps_until_wolf_starves
        self.num_steps_until_grass_grows = num_steps_until_grass_grows
        self.num_steps_until_grass_regenerates = num_steps_until_grass_regenerates

        self.grid = mesa.space.MultiGrid(grid_size, grid_size, torus = False)
        
        self.datacollector = DataCollector(
            model_reporters = {
                'Sheep' : lambda m : m.get_num_sheep(),
                'Wolves' : lambda m : m.get_num_wolves(),
                'Grass' : lambda m : m.get_num_grass()
                }
            )

        self.status_text = '' # text to be displayed in the UI

        # place sheep
        for _ in range(num_sheep):
            valid_pos = self.get_empty_positions()
            sheep_pos = self.random.choice(valid_pos)
            self.spawn_sheep(sheep_pos)

        # place wolves
        for _ in range(num_wolves):
            valid_pos = self.get_empty_positions()
            wolf_pos = self.random.choice(valid_pos)
            self.spawn_wolf(wolf_pos)

        # place grass
        for _ in range(num_grass):
            valid_pos = self.get_empty_positions()
            grass_pos = self.random.choice(valid_pos)
            self.spawn_grass(grass_pos)
        
        self.datacollector.collect(self)

    def spawn_sheep(self, pos):
        sheep = SheepAgent(self, self.num_steps_until_sheep_starves, self.num_steps_until_sheep_breeds)
        self.grid.place_agent(sheep, pos)

    def spawn_wolf(self, pos):
        wolf = WolfAgent(self, self.num_steps_until_wolf_breeds, self.num_steps_until_wolf_starves)
        self.grid.place_agent(wolf, pos)

    def spawn_grass(self, pos):
        grass = GrassAgent(self, self.num_steps_until_grass_grows, self.num_steps_until_grass_regenerates)
        self.grid.place_agent(grass, pos)

    def get_empty_positions(self):
        empty_pos = []
        for contents, (x, y) in self.grid.coord_iter():
            if not contents:
                empty_pos.append((x, y))
        return empty_pos

    def get_num_sheep(self):
        return sum(1 for a in self.agents if a.type == 'sheep')

    def get_num_wolves(self):
        return sum(1 for a in self.agents if a.type == 'wolf')

    def get_num_grass(self):
        return sum(1 for a in self.agents if a.type == 'grass' and a.isAvailable == True)

    def step(self):

        num_sheep = self.get_num_sheep()
        num_wolves = self.get_num_wolves()

        # no more sheep, both populations will go extinct
        if num_sheep <= 0:
            self.status_text = 'Simulation ended. Sheep extinct.'
            self.running = False
            return
    
        # sheep fill the entire grid
        # if num_sheep >= self.grid.width * self.grid.height:
        #     self.status_text = f'Simulation ended. Sheep increased uncontrollably. NUM_SHEEPS: {num_sheep}'
        #     self.running = False
        #     return

        if num_wolves <= 0:
            self.status_text = 'Simulation ended. Wolf extinct.'
            self.running = False
            return

        if num_wolves >= self.grid.width * self.grid.height:
            self.status_text = f'Simulation ended. Wolf increased uncontrollably. NUM_WOLVES: {num_wolves}'
            self.running = False
            return
            
        self.agents.shuffle_do('step')
        self.status_text = 'Simulation running...'

        self.datacollector.collect(self)

       
def agent_portrayal(agent):

    if agent.type == 'sheep':
        portrayal = {
            'color': 'blue',
            'size' : 100,
            'marker' : 'o',
            'zorder' : 2
            }
    elif agent.type == 'wolf':
        portrayal = {
            'color': 'red',
            'size' : 150,
            'marker' : 'v',
            'zorder' : 2
            }
    elif agent.type == 'grass':
        if agent.isAvailable == True:
            portrayal = {
                'color': 'green',
                'size': 100,
                'marker': 'v',
                'zorder': 2
            }
        else:
            portrayal = {
                'size': 0
            }
    else:
        portrayal = {}

    return portrayal

def status_label(model):
    return sl.Card(
        sl.Markdown(model.status_text),
        style={"minWidth": "160px", "padding": "8px"}
        )

if __name__ == '__main__':

    model_params = {
        'grid_size' : {
            'type' : 'SliderInt',
            'value' : GRID_SIZE,
            'label' : 'Grid Size',
            'min' : 8, 
            'max' : 32,
            'step' : 1
            },
        'num_sheep' : {
            'type' : 'SliderInt', 
            'value' : NUM_SHEEP,
            'label' : 'Number of Sheep',
            'min' : 5,
            'max' : 100
            },
        'num_wolves' : {
            'type' : 'SliderInt', 
            'value' : NUM_WOLVES,
            'label' : 'Number of Wolves',
            'min' : 5,
            'max' : 100
            },
        'num_grass': {
            'type' : 'SliderInt', 
            'value' : NUM_GRASS,
            'label' : 'Number of Grass',
            'min' : 5,
            'max' : 100
        },
        'num_steps_until_sheep_breeds' : {
            'type' : 'SliderInt',
            'value' : NUM_STEPS_UNTIL_SHEEP_BREEDS,
            'label' : 'Steps until sheep breeds',
            'min' : 1,
            'max' : 10
            },
        'num_steps_until_sheep_starves' : {
            'type' : 'SliderInt',
            'value' : NUM_STEPS_UNTIL_SHEEP_STARVES,
            'label' : 'Steps until sheep starves',
            'min' : 1,
            'max' : 50
        },
        'num_steps_until_wolf_breeds' : {
            'type' : 'SliderInt',
            'value' : NUM_STEPS_UNTIL_WOLF_BREEDS,
            'label' : 'Steps until wolf breeds',
            'min' : 1,
            'max' : 10
            },
        'num_steps_until_wolf_starves' : {
            'type' : 'SliderInt',
            'value' : NUM_STEPS_UNTIL_WOLF_STARVES,
            'label' : 'Steps until wolf starves',
            'min' : 1,
            'max' : 50
            },
        'num_steps_until_grass_grows': {
            'type' : 'SliderInt',
            'value' : NUM_STEPS_UNTIL_GRASS_GROWS,
            'label' : 'Steps until grass grows',
            'min' : 1,
            'max' : 50
            },
        'num_steps_until_grass_regenerates': {
            'type' : 'SliderInt',
            'value': NUM_STEPS_UNTIL_GRASS_REGENERATES,
            'label' : 'Steps until grass regenerates',
            'min': 1,
            'max': 50
            }
        }

    my_model = PredatorPreyModel(
        grid_size=GRID_SIZE,
        num_grass=NUM_GRASS,
        num_sheep=NUM_SHEEP,
        num_steps_until_grass_grows=NUM_STEPS_UNTIL_GRASS_GROWS,
        num_steps_until_sheep_breeds=NUM_STEPS_UNTIL_SHEEP_BREEDS,
        num_steps_until_sheep_starves=NUM_STEPS_UNTIL_SHEEP_STARVES,
        num_steps_until_wolf_breeds=NUM_STEPS_UNTIL_WOLF_BREEDS,
        num_steps_until_wolf_starves=NUM_STEPS_UNTIL_WOLF_STARVES,
        num_steps_until_grass_regenerates=NUM_STEPS_UNTIL_GRASS_REGENERATES,
        num_wolves=NUM_WOLVES
    )

    space_component = make_space_component(agent_portrayal = agent_portrayal)

    plot_component = make_plot_component(['Sheep', 'Wolves', 'Grass'])

    page = SolaraViz(
        model = my_model, 
        components = [space_component, plot_component, status_label],
        model_params = model_params,
        name = 'Predator-Prey'
        )
