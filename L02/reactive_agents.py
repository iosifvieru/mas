import mesa
from mesa.visualization import SolaraViz, make_space_component, make_plot_component
from mesa.datacollection import DataCollector

class ExplorerAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        self.type = 'explorer'
        self.home_pos = self.model.home.pos
        
    def step(self):
        old_pos = self.pos

        # chech if agent has landed on a resource
        resource = self.model.contains_resource(self.pos)

        if resource:
            self.move_home()
            self.model.grid.move_agent(resource, self.pos)
            if self.pos == self.home_pos: # arrived home with a resource
                self.model.remove_resource(resource)
                resource = None # the agent should resume exploring
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
                 num_explorers = 5,
                 num_resources = 5,
                 uniform_resource_distribution = True,
                 width = 9, height = 9):
        super().__init__()

        self.total_moves = 0

        self.grid = mesa.space.MultiGrid(width, height, torus = False)
            
        # to add datacollector ...
        global ALL_AGENTS_MOVE_COUNT
        ALL_AGENTS_MOVE_COUNT = 0

        # place home base
        self.home = HomeAgent(self)
        self.grid.place_agent(self.home, (width//2, height//2))

        # place resources
        self.place_resources(num_resources=num_resources, uniform_distribution=uniform_resource_distribution)

        # place explorers
        valid_pos = self.get_empty_positions()
        for _ in range(num_explorers):
            explorer = ExplorerAgent(self)
            explorer_pos = self.random.choice(valid_pos)
            self.grid.place_agent(explorer, explorer_pos)

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
        current_num_resources = self.get_num_resources()
        if current_num_resources == 0:
            print(f'\n\nDone. Resources collected in {self.steps} steps, all agents made {self.total_moves} moves.')
            self.running = False

def agent_portrayal(agent):

    if agent.type == 'home':
        portrayal = {
            'color' : 'red',
            'size' : 150,
            'marker' : 'o',
            'zorder' : 0
            }
    elif agent.type == 'resource':
        portrayal = {
            'color' : 'lightgreen',
            'size' : 200,
            'marker' : 's',
            'zorder' : 1
            }
    elif agent.type == 'explorer':
        portrayal = {
            'color' : 'blue',
            'size' : 100,
            'marker' : 'o',
            'zorder' : 2
            }
    else:
        portrayal = {}

    return portrayal

if __name__ == '__main__':
    model_params = {
        'num_explorers': {
            'type' : 'SliderInt',
            'value' : 5,
            'label'  : 'Number of Explorers',
            'min' : 1,
            'max' : 10,
            'step' : 1
            },

        'num_resources': {
            'type' : 'SliderInt',
            'value' : 5,
            'label'  : 'Number of Resources',
            'min' : 1,
            'max' : 10,
            'step' : 1
            },

        'uniform_resource_distribution': {
                "type": "Checkbox",
                "value": True,
                "label": "Uniform resource distribution?"
            },
        }

    my_model = ExplorerModel(num_explorers = 5,
                             num_resources = 5,
                             uniform_resource_distribution = True,
                             width = 9,
                             height = 9)

    space_component = make_space_component(agent_portrayal = agent_portrayal)

    page = SolaraViz(
        model = my_model,
        components = [space_component],
        model_params = model_params,
        name = 'Explorer Agents'
        )

    page


