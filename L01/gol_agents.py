# Vieru Iosif 
# 12.10.2026
# 
# The universe of the Game of Life is an infinite, two-dimensional orthogonal grid of
# square cells, each of which is in one of two possible states, live or dead (or populated
# and unpopulated, respectively). Every cell interacts with its eight neighbours (its Moore
# neighborhood), which are the cells that are horizontally, vertically, or diagonally
# adjacent. At each step in time, the following transitions occur:
# 1.​ Any live cell with fewer than two live neighbours dies, as if by underpopulation.
# 2.​ Any live cell with two or three live neighbours lives on to the next generation.
# 3.​ Any live cell with more than three live neighbours dies, as if by overpopulation.
# 4.​ Any dead cell with exactly three live neighbours becomes a live cell, as if by
# reproduction.
# https://en.wikipedia.org/wiki/Conway%27s_Game_of_Life

import mesa
import random 
from mesa.visualization import SolaraViz, make_space_component

GRID_SIZE = 10
NUM_AGENTS =  GRID_SIZE*GRID_SIZE
DENSITY = 0.5
SEED = random.randint(0, 100)

class CellAgent(mesa.Agent):
    def __init__(self, model, alive=True):
        super().__init__(model)
        self.alive = alive
        self.next_state = False

    def step(self):
        neighbours = self.model.grid.get_neighbors(self.pos, 
                                                moore = True,
                                                include_center = False,
                                                radius  = 1)

        no_alive_neigh = sum(1 for i in neighbours if i.alive is True)

        if self.alive is True:
            if no_alive_neigh < 2:
                self.next_state = False # dies as if by underpopulation

            elif no_alive_neigh == 2 or no_alive_neigh == 3:
                self.next_state = True # remains alive to the next generation

            elif no_alive_neigh > 3:
                self.next_state = False # dies as if by overpopulation

        elif self.alive is False and (no_alive_neigh == 3):
            self.next_state = True # becomes a live cell - reproduction

    def advance(self):
        self.alive = self.next_state

def agent_portrayal(agent):
    if agent.alive:
        return {'color': 'black', 'size': 100, 'marker': 'o'}
    else:
        return {'color': 'white', 'size': 100, 'marker': 'o'}
    
class GridModel(mesa.Model):
    def __init__(self, 
                num_agents = NUM_AGENTS, 
                grid_size = GRID_SIZE,
                density = DENSITY,
                seed = SEED):
            
            super().__init__(seed = seed)
            self.grid = mesa.space.MultiGrid(grid_size, grid_size, torus = False)

            for _ in range(num_agents):
                empty_cells = [(x, y) for (cell_content, (x, y)) in self.grid.coord_iter()
                            if len(cell_content) == 0]
                init_pos = self.random.choice(empty_cells)

                is_alive = self.random.random() < density
                a = CellAgent(self, alive=is_alive)

                self.grid.place_agent(a, init_pos)

    def step(self):
        self.agents.do('step')
        self.agents.do('advance')
        
if __name__ == '__main__':

    model_params = {
        'grid_size' : {
            'type' : 'SliderInt',
            'value' : GRID_SIZE, 
            'label' : 'Grid Size', 
            'min' : 8, 
            'max': 26,
            'step' : 1
            },
        'density' : {
            'type' : 'SliderFloat',
            'value' : DENSITY, 
            'label' : 'Density', 
            'min' : 0, 
            'max': 1,
            'step' : 0.1
            }
        }

    my_model = GridModel()
    
    grid_component = make_space_component(agent_portrayal = agent_portrayal)

    page = SolaraViz(
        model = my_model, 
        components = [grid_component],
        model_params = model_params,
        name = 'Conway s Game of Life'
        )

    page
