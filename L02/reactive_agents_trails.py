import mesa
from mesa.visualization import SolaraViz, make_space_component, make_plot_component
from mesa.datacollection import DataCollector
from mesa.space import PropertyLayer
import solara as sl
import numpy as np

DEFAULT_NUM_EXPLORERS = 5
DEFAULT_NUM_RESOURCES = 5
DEFAULT_GRID_SIZE = 17
DEFAULT_WEIGHT_DECAY = 0.08

class ExplorerAgent(mesa.Agent):
    def __init__(self, model, grid_size=DEFAULT_GRID_SIZE):
        super().__init__(model)
        self.type = 'explorer'
        self.home_pos = self.model.home.pos
        self.grid_size = grid_size
        
    def step(self):
        old_pos = self.pos

        # chech if agent has landed on a resource
        resource = self.model.contains_resource(self.pos)


        if resource:
            self.model.weight_layer.data[self.pos] = 1
            self.move_home()
            self.model.grid.move_agent(resource, self.pos)
            if self.pos == self.home_pos: # arrived home with a resource
                self.model.remove_resource(resource)
                resource = None # the agent should resume exploring
        elif self.model.weight_layer.data[self.pos] > 0:
            self.move_away_from_home()
        else:
            self.move_explore()

        if self.pos != old_pos:
            self.model.total_moves += 1

    def move_explore(self):
        # move in a random neighboring position
        
        neighbor_pos = self.model.grid.get_neighborhood(self.pos, 
                                                        moore = False, # no diagonals
                                                        include_center = False, 
                                                        radius = 1)
        # avoid collision with other explorers
        valid_pos = []
        for p in neighbor_pos:
            neighbor_agents = self.model.grid.get_cell_list_contents(p)
            if not neighbor_agents: 
                # empty cell
                valid_pos.append(p)
            elif not any([a.type == 'explorer' for a in neighbor_agents]): 
                # cell doesn't contain explorer agents
                valid_pos.append(p) 
        
        if valid_pos:
            new_pos = self.random.choice(valid_pos)
            self.model.grid.move_agent(self, new_pos)

    def move_home(self):
        # move in a direction towards home
        (x, y) = self.pos
        (xh, yh) = self.home_pos
        dx = x - xh
        dy = y - yh
        sign_dx = 1 if dx > 0 else -1 if dx < 0 else 0
        sign_dy = 1 if dy > 0 else -1 if dy < 0 else 0

        if abs(dx) > abs(dy):
            new_pos = (x - sign_dx, y)
        else:
            new_pos = (x, y - sign_dy)

        self.model.grid.move_agent(self, new_pos)

    def move_away_from_home(self):
        # move in a direction away from home
        (x, y) = self.pos
        (xh, yh) = self.home_pos
        dx = x - xh
        dy = y - yh
        sign_dx = 1 if dx > 0 else -1 if dx < 0 else 0
        sign_dy = 1 if dy > 0 else -1 if dy < 0 else 0

        if abs(dx) > abs(dy):
            new_x = x + sign_dx
            if new_x < 0:
                new_x = 0
            if new_x >= self.grid_size:
                new_x = self.grid_size - 1

            new_pos = (new_x, y)
        else:
            new_y = y + sign_dy
            if new_y < 0:
                new_y = 0
            if new_y >= self.grid_size:
                new_y = self.grid_size - 1

            new_pos = (x, new_y)
        self.model.grid.move_agent(self, new_pos)

class ResourceAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        self.type = 'resource'

    def step(self):
        pass

class HomeAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        self.type = 'home'

    def step(self):
        pass

class ExplorerModel(mesa.Model):
    def __init__(self, 
                 num_explorers = DEFAULT_NUM_EXPLORERS,
                 num_resources = DEFAULT_NUM_RESOURCES, 
                 grid_size = DEFAULT_GRID_SIZE,
                 uniform_resource_distribution = True,
                 weight_decay = DEFAULT_WEIGHT_DECAY):
        super().__init__()

        self.total_moves = 0
        self.grid = mesa.space.MultiGrid(grid_size, grid_size, torus = False)

        self.weight_layer = PropertyLayer(name = 'cell_weight', 
                                          width = grid_size, 
                                          height = grid_size, 
                                          default_value = 0.0, 
                                          dtype = float)

        self.weight_layer.data = np.zeros([grid_size, grid_size], dtype = float)

        self.grid.add_property_layer(self.weight_layer)

        self.weight_decay = float(weight_decay)

        self.datacollector = DataCollector(
            model_reporters = {'Resource Count' : lambda m : m.get_num_resources()}
            )

        self.status_text = '' # text displayed in the UI

        # place home base
        self.home = HomeAgent(self)
        self.grid.place_agent(self.home, (grid_size//2, grid_size//2))

        # place resources
        self.place_resources(num_resources=num_resources, uniform_distribution=uniform_resource_distribution)

        # place explorers
        valid_pos = self.get_empty_positions()
        for _ in range(num_explorers):
            explorer = ExplorerAgent(self, grid_size=grid_size)
            explorer_pos = self.random.choice(valid_pos)
            self.grid.place_agent(explorer, explorer_pos)

        self.datacollector.collect(self)

    def place_resources(self, num_resources, uniform_distribution):
        if uniform_distribution:
            valid_pos = self.get_empty_positions()
            for _ in range(num_resources):
                if not valid_pos:
                    break
                res_pos = self.random.choice(valid_pos)
                resource = ResourceAgent(self)
                self.grid.place_agent(resource, res_pos)
                valid_pos.remove(res_pos)
        else:
            while num_resources > 0:
                valid_pos = self.get_empty_positions()
                if not valid_pos:
                    break

                res_pos = self.random.choice(valid_pos)
                resource = ResourceAgent(self)
                self.grid.place_agent(resource, res_pos)
                num_resources -= 1

                rand_nr_neigh = self.random.randint(0, num_resources // 2)
                for _ in range(rand_nr_neigh):
                    empty_cells = [
                        cell for cell in self.grid.get_neighborhood(
                            res_pos, moore=False, include_center=False
                        )
                        if self.grid.is_cell_empty(cell)
                    ]
                    if not empty_cells or num_resources <= 0:
                        break

                    temp_res_pos = self.random.choice(empty_cells)
                    temp_res = ResourceAgent(self)
                    self.grid.place_agent(temp_res, temp_res_pos)
                    num_resources -= 1
    
    def get_empty_positions(self):
        empty_pos = []
        for contents, (x, y) in self.grid.coord_iter():
            if not contents:
                empty_pos.append((x, y))
        return empty_pos
    
    def get_num_resources(self):
        return sum(1 for a in self.agents if a.type == 'resource')

    def contains_resource(self, pos):
        # check if there is a resource at current position, 
        # return resource agent or None
        agents_at_pos = self.grid.get_cell_list_contents(pos)
        if not agents_at_pos:
            return None
        resources_at_pos = [a for a in agents_at_pos if a.type == 'resource']
        if not resources_at_pos:
            return None

        return resources_at_pos[0]

    def remove_resource(self, agent):
        self.grid.remove_agent(agent)
        self.agents.remove(agent)

    def step(self):
        self.agents.shuffle_do('step')
        self.weight_layer.data -= self.weight_decay

        current_num_resources = self.get_num_resources()

        self.datacollector.collect(self)

        self.status_text = f'Resources: {current_num_resources}'
        
        if current_num_resources == 0:
            self.status_text += f'\n\nDone. Resources collected in {self.steps} steps. total moves: {self.total_moves}'
            self.running = False
        
def agent_portrayal(agent):

    if agent.type == 'home':
        portrayal = {
            'color' : 'red',
            'size' : 150,
            'marker' : 'o',
            'zorder' : 1
            }
    elif agent.type == 'resource':
        portrayal = {
            'color' : 'lightgreen',
            'size' : 200,
            'marker' : 's',
            'zorder' : 2
            }
    elif agent.type == 'explorer':
        portrayal = {
            'color' : 'blue',
            'size' : 100,
            'marker' : 'v',
            'zorder' : 3
            }
    else:
        portrayal = {}

    return portrayal

def property_layer_portrayal():
    portrayal = {
        'cell_weight': {
            'colormap' : 'Oranges', 
            'alpha' : 1.0, 
            'colorbar' : False,
            'vmin' : 0,
            'vmax' : 1
            }
        }
    return portrayal

def status_label(model):
    return sl.Card(
        sl.Markdown(model.status_text),
        style={"minWidth": "160px", "padding": "8px"}
    )

if __name__ == '__main__':

    model_params = {
        'num_explorers': {
            'type' : 'SliderInt',
            'value' : DEFAULT_NUM_EXPLORERS,
            'label'  : 'Number of Explorers',
            'min' : 1,
            'max' : 10,
            'step' : 1
            },

        'num_resources': {
            'type' : 'SliderInt',
            'value' : DEFAULT_NUM_RESOURCES,
            'label'  : 'Number of Resources',
            'min' : 1,
            'max' : 10,
            'step' : 1
            },

        'grid_size' : {
            'type' : 'SliderInt',
            'value' : DEFAULT_GRID_SIZE,
            'label'  : 'Grid Size',
            'min' : 9,
            'max' : 21,
            'step' : 1
            },

        'weight_decay' : {
            'type' : 'InputText',
            'value' : DEFAULT_WEIGHT_DECAY,
            'label' : 'Weight Decay',
            },

        'uniform_resource_distribution': {
                "type": "Checkbox",
                "value": True,
                "label": "Uniform resource distribution?"
            },
        }

    my_model = ExplorerModel(uniform_resource_distribution = True)

    space_component = make_space_component(agent_portrayal = agent_portrayal,
                                           propertylayer_portrayal = property_layer_portrayal())

    plot_component = make_plot_component('Resource Count')
                                           
    page = SolaraViz(
        model = my_model,
        components = [space_component, plot_component, status_label],
        model_params = model_params,
        name = 'Explorer Agents'
        )

    page

