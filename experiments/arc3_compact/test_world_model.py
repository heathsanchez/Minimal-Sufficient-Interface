import unittest
from dataclasses import dataclass
import numpy as np
from world_model import MotionModel,run_model_episode

@dataclass
class Frame:
    frame: list
    levels_completed: int
    state: str

class HiddenGrid:
    """Test-only world. The controller receives Frame, never this world state."""
    def __init__(self, mapping=(1,2,3,4), palette=(3,4,9,12), levels=3):
        self.mapping=mapping
        self.floor,self.wall,self.actor,self.accent=palette
        self.level_count=levels
        self.level=self.ticks=0
        self.pos=(7,7)
        self.goal=(2,2)
        self.walkable={(y,x) for y in range(1,10) for x in range(1,10)}
        self.walkable -= {(y,5) for y in range(2,9) if y != 4}
        self.observation_space=self.render()
    def render(self):
        a=np.full((64,64),self.wall,dtype=np.int16)
        for y,x in self.walkable:
            a[y*5:(y+1)*5,x*5:(x+1)*5]=self.floor
        gy,gx=self.goal
        a[gy*5+1:gy*5+4,gx*5+1:gx*5+4]=1
        py,px=self.pos
        a[py*5:py*5+2,px*5:(px+1)*5]=self.accent
        a[py*5+2:(py+1)*5,px*5:(px+1)*5]=self.actor
        a[61:63,4:60]=11
        a[61:63,4:4+(self.ticks%40)]=self.floor
        return Frame([a],self.level,'WIN' if self.level==self.level_count else 'NOT_FINISHED')
    def step(self,action):
        directions=((-1,0),(1,0),(0,-1),(0,1))
        d=directions[self.mapping.index(action)]
        nxt=(self.pos[0]+d[0],self.pos[1]+d[1])
        if nxt in self.walkable:self.pos=nxt
        self.ticks+=1
        if self.pos==self.goal:
            self.level+=1
            self.pos=(7,7)
            self.goal=(2,2)
        self.observation_space=self.render()
        return self.observation_space

class WorldModelTests(unittest.TestCase):
    def test_actual_observation_replay(self):
        import json
        from pathlib import Path
        p=Path(__file__).parent/'observations/arc3-observations.json'
        if not p.exists():self.skipTest('Recorded public observations not installed')
        from types import SimpleNamespace
        t=json.loads(p.read_text())
        f=lambda x:SimpleNamespace(frame=x['frame'],state=x['state'],levels_completed=x['levels_completed'])
        m=MotionModel((1,2,3,4))
        for i in range(1,len(t)):
            m.observe(f(t[i-1]),t[i]['action'],f(t[i]))
        self.assertEqual({a:next(iter(v)) for a,v in m.vectors.items()},
                         {1:(-5,0),2:(5,0),3:(0,-5),4:(0,5)})
        self.assertEqual(m.conflicts,[])
    def test_hidden_mapping_and_palette(self):
        for mapping,palette in [((1,2,3,4),(3,4,9,12)),((4,3,1,2),(5,2,7,13)),((2,1,4,3),(8,6,10,14))]:
            result=run_model_episode(HiddenGrid(mapping,palette),mapping,300)
            self.assertEqual(result['state'],'WIN',result)
            self.assertEqual(result['levels_completed'],3)
            self.assertEqual(result['model_calls'],0)
            self.assertGreater(len(result['level_actions']),0)
    def test_moving_component_is_not_hud(self):
        env=HiddenGrid()
        before=env.observation_space
        after=env.step(1)
        m=MotionModel((1,2,3,4))
        self.assertTrue(m.observe(before,1,after))
        self.assertEqual(len(m.shape),15)
        self.assertEqual(m.vector(1),(-5,0))
    def test_local_obstruction_not_global_rejection(self):
        env=HiddenGrid()
        m=MotionModel((1,2,3,4))
        for _ in range(8):
            b=env.observation_space;a=env.step(1);m.observe(b,1,a)
        self.assertEqual(m.vector(1),(-5,0))
        self.assertIn((m.position,1),m.blocked)
        self.assertTrue(any(k[1]==1 and k[0]!=q for k,q in m.edges.items()))
if __name__=='__main__':unittest.main()
