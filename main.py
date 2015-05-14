#!/usr/bin/env python
#
# Line Battles is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import math
import time
import random
random.seed(time.time())

import argparse

#from OpenGL.GL import *
#from OpenGL.GLU import *

import pygame
import pygame.gfxdraw
from pygame.locals import *



################################################################################
#                                    Debug                                     #
################################################################################

class Stats(object):
  '''Keeps track of statistics about the game.  This counts variables
  (distinguished by their string names), incrementing them by 1 for every call
  to `Stats#inc(varname)`.'''

  MARGIN = 20
  '''The margin between HUD and edge of screen.'''

  stats_object = None
  '''The singleton object.'''

  @classmethod
  def get_stats(cls, screen=None, size=None):
    '''Gets the one and only `Stats` object.

    Args:
      screen, pygame.Screen: The screen.
      size, (int,int): Width and height of the screen (in pixels).

    Returns:
      The one and only `Stats` object.
    '''
    if cls.stats_object is None:
      cls.stats_object = cls(screen, size)
    return cls.stats_object

  def __init__(self, screen, size):
    '''Creates the statistics object.

    Args:
      screen, pygame.Screen: The screen.
      size, (int,int): The width and height of the screen (in pixels).
    '''
    self.screen = screen
    self.size = self.width,self.height = size
    self.font = pygame.font.SysFont("courier", 10, bold=True)
    self.counts = {}

  def reset(self, varname=None):
    '''Resets the variable name `varname` to be 0.

    Args:
      varname, str: The name of the `varname`.
    '''
    if varname is None:
      self.counts = {}
    else:
      self.counts[varname] = 0

  def inc(self, varname):
    '''Increment a variable.  `varname` can be just about anything.

    Args:
      varname, str: The name of the variable.
    '''
    self.counts[varname] = 1 + (varname in self.counts and
                                self.counts[varname] or 0)
    return

  def draw(self):
    '''Draw all the variables and their values on the screen.'''
    x, y = self.width - self.MARGIN, self.MARGIN
    for key in self.counts:
      string = "%s: % 8d" % (key, self.counts[key])
      w, h = self.font.size(string)
      self.screen.blit(self.font.render(string, True, (255, 255, 255)),
                       (x-w, y))
      y += h


class Positional(object):
  '''Something that has a position on the screen.'''
  def __init__(self):
    assert False, "Shouldn't call Positional constructor."

  def move(self, *delta):
    '''Moves this element by the specified amount in the X and Y directions.

    Args:
      delta, (int,int): Amount to increment this ship's position by.

    Returns:
      (int,int): The ship's new (X,Y) position.
    '''
    self.rect = None
    self.pos[0] += delta[0]
    self.pos[1] += delta[1]
    return self.pos


class Ship(Positional):
  '''This class is used for drawing, mainly.  Just pass it some points
  and things, and it'll handle the rest!'''
  def __init__(self, screen, color, points, pos=(0,0), traj=0, size=10):
    '''Create a ship.

    A nontrivial detail: the size parameter is in pixels, but so are the points.
    So if the size is 5 but there's a point in the points list that's something
    like "(40,80)", then the effect will be that the effectual size of the ship
    will be sqrt(40**2+80**2) * 5 = 447.2, so beware.  It is recommended that
    you try to keep the values in the points argument to <= 1.

    Args:
      screen, pygame.Surface: The screen to draw on.
      color, (int,int,int): The (R,G,B) color to draw.
      points, [int]: Points consisting of the line-art
      pos, (int,int): Initial (X,Y) position of the ship
      traj, (int,int): Initial (X,Y) trajectory (0 radians is to the left, 0.5pi
                       is down)
      size, (int,int): Size (w,h) of the ship.
    '''
    self.screen = screen
    self.color = color
    self.ps = points
    self.pos = list(pos)
    self.traj = traj
    self.size = size
    self.speed = 2  # really more like the current max speed
                    #                   (subject to upgrades)

    # `rect` ensures the `bbox` for this is calculated at most once per tick.
    self.rect = None   # i.e., not up-to-date

  def move_forward(self, amt=1.0):
    '''Moves forward relative to this ship's trajectory, `self.traj`.

    Args:
      amt, float: The amount to move by w.r.t. this ship's speed, `self.speed`.
          1.0 is "full speed" and 0.0 is not at all.

    Throws:
      AssertionError: Iff `amt` is O.O.B.
    '''
    assert amt >= 0 and amt <= 1, "amt out of range: %d" % amt
    self.rect = None
    speed = self.speed * amt
    self.pos[0] += math.cos(self.traj) * speed
    self.pos[1] += math.sin(self.traj) * speed

  def rotate(self, dt):
    self.rect = None  # Invalidate rect (will be recomputed).
    self.traj += dt
    while self.traj > 2 * math.pi:
      self.traj -= 2 * math.pi
    while self.traj < 0:
      self.traj += 2 * math.pi

  def _calc_global_ps(self):
    st = math.sin(self.traj) * self.size
    ct = math.cos(self.traj) * self.size
    return [(self.pos[0] + p[0] * ct - p[1] * st,
             self.pos[1] + p[1] * ct + p[0] * st)
            for p in self.ps]

  def _build_rect(self):
    if self.rect is None:
      ps = self._calc_global_ps()
      self.rect = pygame.Rect(ps[0], (1, 1))
      self.rect.unionall_ip([pygame.Rect(p, (1, 1)) for p in ps[1:]])
    return self.rect

  def center(self):
    return self._build_rect().center

  def draw(self):
    pygame.gfxdraw.filled_polygon(self.screen,
            self._calc_global_ps(), self.color + (80,))
    pygame.draw.lines(self.screen, self.color, True, self._calc_global_ps())

  def collides(self, that):
    if isinstance(that, Ship) or isinstance(that, Upgrade):
      return self._build_rect().colliderect(that._build_rect())
    elif isinstance(that, Bullet):
      # Bullets vary greatly in how their collision detection
      # is meant to work.
      return that.collides(self)
    else:
      print 'Warning! Ship-%d collision detection??' % type(that)
      return False



class Player(Ship):
  '''This should be unique in that it's the only ship that can also fire guns
  and stuff.'''
  def __init__(self, screen):
    super(Player, self).__init__(screen, (200, 200, 255),
                                 ((0, -1), (2, -1), (0, -2), (-2, -1),
                                  (-2, 1), (0, 2), (2, 1), (0, 1)),
                                 size = 5)
    self.screen = screen
    self.reset()
    self.shields = 0
    self.radius = int(self.size * max([(i*i + j*j)**.5 for i,j in self.ps]))

  def reset(self):
    self.last_fire_time = 0
    self.fire_delay = 100 # ms
    self.exploding = False
    self.expl_prog = 0
    self.gun = Gun(self.screen, 0)
    self.speed = 4
    self.score = 0

  def okay_to_fire(self):
    ticks = pygame.time.get_ticks()
    if self.last_fire_time + self.fire_delay <= ticks:
      self.last_fire_time = ticks
      return True
    return False

  def draw(self):
    if self.exploding:
      self.expl_prog += .5
      pygame.draw.circle(self.screen, (255,0,0),
          map(int, self.pos), int(self.expl_prog))
    else:
      Ship.draw(self)
      if self.shields > 0:
        r = 255
        g = min(128 * ((self.shields / self.radius) % 3), 255)
        b = min(128 * ((self.shields / (3 * self.radius))), 255)
        if b == 255: g = 255
        freq = .5 + 1.5 * ((self.shields % self.radius) - 1) / self.radius
        a = 40 * (1 + math.sin(time.time() * math.pi * 2 * freq))
        pygame.gfxdraw.filled_circle(self.screen, int(self.pos[0]),
                int(self.pos[1]), self.radius, (r,g,b,a))
        pygame.draw.circle(self.screen, (r,g,b), map(int, self.pos),
                                                self.radius, 1)

  def fire(self, traj):
    return self.okay_to_fire() and self.gun.fire(self.pos, traj) or ()

  def hit(self):
    if self.shields <= 0:
      self.explode()
      return
    self.shields -= 1

  def explode(self):
    self.exploding = True

  @classmethod
  def spawn_at(cls, screen, x, y):
    ship = cls(screen)
    ship.pos = [x,y]
    return ship



################################################################################
#                                   Baddies                                    #
################################################################################

class Baddie(Ship):
  '''A basic "bad guy".  This doesn't actually do anything, it just sets
  up a ship in a "bad guy" kind of a way.'''
  def __init__(self, screen, color, pos, traj, size, geom):
    super(Baddie, self).__init__(screen, color, geom, size = size)
    self.pos = list(pos)
    self.traj = traj
    self.speed = 1
    self.score = 100

  def upgrade(self):
    '''Returns a tuple of upgrades (baddie-specific), which may be empty.'''
    assert False, "Can't make instances of this class."

  def tick(self):
    '''Perform one frame of action.  This method just throws an error.  You MUST
    overwrite it.

    Raises:
      AssertionError: Always.  Overwrite this method.
    '''
    assert False, "Shouldn't make instances of this class."

  def _calc_upgrade(self, **kwargs):
    '''Calculates what upgrades to give based on `kwargs`.  Each argument name
    is interpreted as a class name and each argument value is interpreted as the
    chance that the class will be added.  For example, passing:
        BulletUpgrade=200
    means that a BulletUpgrade should be included with a 1/200 chance.

    Args:
      kwargs: The names and changes of spawning specific classes.
    '''
    return [eval("%s(self.screen, self.pos)" % k)
            for k, v in kwargs.iteritems()
            if random.randrange(v) < 1]


class Wiggler(Baddie):
  '''A random walker "bad guy".'''
  def __init__(self, screen, pos, traj):
    super(Wiggler, self).__init__(screen, (0,255,0), pos, traj, 5,
            ((1,1), (1,-1), (-1,-1), (-1, 1)))
    self.score = 200

  def upgrade(self):
    '''Returns one or many upgrades based on probability.

    Returns:
      Upgrade: The upgrade this returns on death.
    '''
    return super(Wiggler, self)._calc_upgrade(BulletUpgrade=200,
                                              SpeedUpgrade=200,
                                              ShieldUpgrade=200)

  def tick(self):
    '''Perform one frame of action.'''
    self.traj += random.randrange(-100,100,1) / 1000.
    while self.traj > 2 * math.pi:
      self.traj -= 2 * math.pi
    while self.traj < 0:
      self.traj += 2 * math.pi
    self.move_forward(1)


class FastWiggler(Wiggler):
  '''Same as wiggler, but goes faster.'''
  def __init__(self, screen, pos, traj):
    '''See Wiggler.__init__(...)'''
    super(FastWiggler, self).__init__(screen, pos, traj)
    self.color = (255,127,127)
    self.speed = 2
    self.score = 400


class Homer(Baddie):
  '''A fast "bad guy" that follows the player.'''
  def __init__(self, screen, pos, traj):
    super(Homer, self).__init__(screen, (255,0,255), pos, traj, 5,
            ((2,0), (0,-1), (-2,0), (0,1)))
    self.speed = 2

  def upgrade(self):
    '''Returns one or many upgrades based on probability.

    Returns:
      Upgrade: The upgrade this returns on death.
    '''
    return super(Homer, self)._calc_upgrade(BulletUpgrade=300,
                                            SpeedUpgrade=100,
                                            ShieldUpgrade=200)

  def tick(self):
    '''Perform one frame of action.'''
    dx = Main.get_main().player.pos[0] - self.pos[0]
    dy = Main.get_main().player.pos[1] - self.pos[1]
    self.traj = math.atan2(dy, dx)
    self.move_forward()

class Shooter(Baddie):
  FIRE_RATE = 4000
  def __init__(self, screen, pos, traj):
    super(Shooter, self).__init__(screen, (255,0,127), pos, traj, 5,
            ((1,0), (-1,-1), (-1,1)))
    self.speed = 2
    self.score = 200
    self.gun = Gun(screen, 0, 'bad')
    self.last_fired = 0

  def upgrade(self):
    '''Returns one or many upgrades based on probability.

    Returns:
      Upgrade: The upgrade this returns on death.
    '''
    return super(Shooter, self)._calc_upgrade(BulletUpgrade=100,
                                              SpeedUpgrade=400,
                                              ShieldUpgrade=200)

  def _fire(self):
    self.last_fired = pygame.time.get_ticks()
    return self.gun.fire(self.pos, self.traj)

  def okay_to_fire(self):
    return self.last_fired + self.FIRE_RATE <= pygame.time.get_ticks()

  def tick(self):
    if random.randrange(100) < 1:
      self.traj = random.randrange(200) * math.pi / 100
    self.move_forward()
    if self.okay_to_fire():
      return self._fire()




################################################################################
#                                Guns / Bullets                                #
################################################################################

class Bullet(object):
  def __init__(self, screen, pos, traj, side):
    self.screen = screen
    self.pos = list(pos)
    self.traj = traj
    self.side = side
    self.speed = 8
    self.length = 10
    self.color = 255,0,0

  def collides(self, that):
    return isinstance(that, Ship) and \
        that._build_rect().collidepoint(self.pos)

  def _calc_shift(self):
    return [ self.speed * math.cos(self.traj),
             self.speed * math.sin(self.traj) ]

  def _calc_tail_pos(self):
    return [ self.pos[0] - self.length * math.cos(self.traj),
             self.pos[1] - self.length * math.sin(self.traj) ]

  def draw(self):
    pygame.draw.line(self.screen, self.color,
                     self.pos, self._calc_tail_pos(), 2)

  def tick(self):
    self.move_forward()

  def move_forward(self):
    shift = self._calc_shift()
    self.pos[0] += shift[0]
    self.pos[1] += shift[1]

class Gun(object):
  SIDES = ('good', 'bad')

  def __init__(self, screen, num_bullets, side = 'good'):
    assert side in self.SIDES, 'Invalid side: %s' % side
    self.screen = screen
    self.power = num_bullets
    self.side = side

  def fire(self, pos, traj):
    bullets = []
    for i in xrange(-self.power, self.power + 1, 2):
      bullets.append(Bullet(self.screen, pos, traj + i / 50., self.side))
    return bullets



################################################################################
#                            Spawn Points / Levels                             #
################################################################################

class SpawnPoint(object):
  def __init__(self, screen, size, x, y, baddies_array):
    self.screen = screen
    self.pos = [x,y]
    self.baddies = baddies_array
    self.traj = math.atan2(size[0] / 2 - y, size[1] / 2 - x)
    self.queue = []
    self.paused = False

  def pause(self):
    self.paused = True

  def resume(self):
    self.paused = False

  def spawn(self, baddie_type = Wiggler):
    self.baddies.append(baddie_type(self.screen, self.pos, self.traj))

  def queue_spawn(self, baddie_type):
    self.queue.append(baddie_type)

  def tick(self):
    if self.paused: return
    if len(self.queue) > 0 and random.randrange(100) < 20:
      self.spawn(self.queue[0])
      del self.queue[0]

  def draw(self):
    pass

  def clear(self):
    self.queue = []

class Level(object):
  def __init__(self, screen, size, spawn_point_array, greeting, progression):
    '''Creates a level.
    screen: SDL surface to draw to
    spawn_point_array: the spawn points
    greeting: the string to display when the level starts
    progression: The progression of the level.  Expected is a list of
                 4-tuples, where each tuple is:
                   1: pause time before wave start
                   2: index of spawn point to spawn at.
                   3: type of baddie to spawn
                   4: number of baddies to spawn'''
    self.screen = screen
    self.spawns = spawn_point_array

    self.font = pygame.font.SysFont("courier", 30, bold = True)
    self.greeting = greeting
    w,h = self.font.size(self.greeting)
    self.greeting_pos = (size[0] - w) / 2, (size[1] - h) / 2

    self.progression = progression
    self.prog_i = -1
    self.paused = False

  def started(self):
    return self.prog_i >= 0

  def pause(self):
    self.paused = pygame.time.get_ticks()
    for sp in self.spawns: sp.pause()

  def resume(self):
    for sp in self.spawns: sp.resume()
    self.start_time += pygame.time.get_ticks() - self.paused
    self.paused = False

  def start(self):
    self.paused = False
    self.prog_i = 0
    self.start_time = pygame.time.get_ticks()

  def _p(self):
    if self.prog_i < len(self.progression):
      return self.progression[self.prog_i]
    else:
      return (9e9999,-1,None,0)

  def tick(self):
    if self.paused: return

    # Check/spawn queue
    if self.prog_i < len(self.progression):
      while self._p()[0] <= pygame.time.get_ticks() - self.start_time:
        for i in xrange(self._p()[3]):
          self.spawns[self._p()[1]].queue_spawn(self._p()[2])
        self.prog_i += 1

  def jump_to_next_wave(self):
    if self.prog_i != 0 and self.prog_i < len(self.progression):
      self.start_time = pygame.time.get_ticks() - self._p()[0]
    self.tick()

  def draw(self):
    if self.prog_i == 0:
      self.screen.blit(self.font.render(self.greeting, False,
              (255,255,255)), self.greeting_pos)

  def done(self):
    return self.prog_i >= len(self.progression)



################################################################################
#                                  User Input                                  #
################################################################################

class Input(object):
  def __init__(self, player, space):
    '''

    Args:
      player, Player: The player.
      space, CollisionSpace: The space where collisions are computed..
    '''
    self.player = player
    self.space = space
    if pygame.joystick.get_count() > 0:
      self.js = pygame.joystick.Joystick(0)
      self.js.init()
      if self.js.get_numaxes() < 4:
        self.js.quit()
        self.js = None
        logger.wrn("Could joystick does not have at least 4 axes. (%d)" %
            self.js.get_numaxes())
        return
      print 'using %d axes' % self.js.get_numaxes()
    else:
      self.js = None

  def tick(self):
    '''Do one tick; handles input.'''
    keys = pygame.key.get_pressed() if self.js is None else None

    js_dx = self._get_mx(keys)
    js_dy = self._get_my(keys)
    self.player.traj = math.atan2(js_dy, js_dx)
    if abs(js_dx) > 0.1 or abs(js_dy) > 0.1:
      amt = math.sqrt(js_dx * js_dx + js_dy * js_dy)
      self.player.move_forward(1.0 if amt > 1 else -1.0 if amt < -1 else amt)

    js_fx = self._get_fx(keys)
    js_fy = self._get_fy(keys)
    if abs(js_fx) > 0.1 or abs(js_fy) > 0.1:
      for b in self.player.fire(math.atan2(js_fy, js_fx)):
        self.space.add(b)

  def _get_mx(self, keys):
    '''Gets movement in the X direction (in [-1,1] for [left,right]).

    Args:
      keys, [bool]: Array of key states.
    '''
    if self.js is None:
      return 1.0 if keys[pygame.K_f] else -1.0 if keys[pygame.K_s] else 0.0
    return self.js.get_axis(0)

  def _get_my(self, keys):
    '''Gets movement in the Y direction (in [-1,1] for [top,bottom]).

    Args:
      keys, [bool]: Array of key states.
    '''
    if self.js is None:
      return 1.0 if keys[pygame.K_d] else -1.0 if keys[pygame.K_e] else 0.0
    return self.js.get_axis(1)

  def _get_fx(self, keys):
    '''Gets fire direction in X (in [-1,1] for [left,right]).

    Args:
      keys, [bool]: Array of key states.
    '''
    if self.js is None:
      return 1.0 if keys[pygame.K_l] else -1.0 if keys[pygame.K_j] else 0.0
    return self.js.get_axis(3)

  def _get_fy(self, keys):
    '''Gets fire direction in Y (in [-1,1] for [top,bottom]).

    Args:
      keys, [bool]: Array of key states.
    '''
    if self.js is None:
      return 1.0 if keys[pygame.K_k] else -1.0 if keys[pygame.K_i] else 0.0
    return self.js.get_axis(2)



################################################################################
#                             Collision Detection                              #
################################################################################

class CollisionSpace(object):
  '''This is an implementation of sub-space partitioning collision detection.'''

  BINSIZE = 50
  '''1-D size of each sub-space (bin).'''
  BUFSIZE = .2
  '''1-D percentage of overlapping space.'''

  def __init__(self, size, player):
    '''Creates the collision space.

    Args:
      size, (int,int): Tuple defining width and height in px.
      player, Player: The player.
    '''
    self.player = player
    self.baddies = []
    self.bullets = []
    self.set_screen_size(size)

  def set_screen_size(self, size):
    '''Sets (or re-sets) the size of the screen.

    Args:
      size, (int,int): Tuple defining width and height of the screen in px.
    '''
    self.size = self.width,self.height = size
    self.cols = size[0] / self.BINSIZE
    self.rows = size[1] / self.BINSIZE

  def empty(self):
    while len(self.baddies) > 0: del self.baddies[-1]
    while len(self.bullets) > 0: del self.bullets[-1]

  def _tick_baddie(self, baddie):
    buls = baddie.tick()
    if buls is not None:
      for b in buls:
        self.add(b)

    # Bounce off the walls.
    rect = baddie._build_rect()
    if rect.left <= 0 or rect.right >= self.width:
      baddie.traj = math.pi - baddie.traj
      while baddie._build_rect().left <= 0:
        baddie.move(1,0)
      while baddie._build_rect().right >= self.width:
        baddie.move(-1,0)
    if rect.top <= 0 or rect.bottom >= self.height:
      baddie.traj = -baddie.traj
      while baddie._build_rect().top <= 0:
        baddie.move(0,1)
      while baddie._build_rect().bottom >= self.height:
        baddie.move(0,-1)

    self._insert_baddie(baddie)

  def tick(self):
    self.bins = []
    for i in xrange(self.cols):
      self.bins.append([])
      for j in xrange(self.rows):
        self.bins[i].append([])

    # update baddies and put them in their bins
    for b in xrange(len(self.baddies)-1,-1,-1):
      baddie = self.baddies[b]
      if isinstance(baddie, Baddie) or isinstance(baddie, Upgrade):
        self._tick_baddie(baddie)
      elif isinstance(baddie, Bullet):
        baddie.tick()
        if baddie.pos[0] < 0 or baddie.pos[0] > self.width or (
           baddie.pos[1] < 0 or baddie.pos[1] > self.height):
          del self.baddies[b]
        else:
          self._insert_baddie(baddie)
      else:
        assert False, "Unrecognized type: %s" % str(type(baddie))

    # Ensure the player is in bounds.
    while self.player._build_rect().left <= 0:
      self.player.move(1,0)
    while self.player._build_rect().right >= self.width:
      self.player.move(-1,0)
    while self.player._build_rect().top <= 0:
      self.player.move(0,1)
    while self.player._build_rect().bottom >= self.height:
      self.player.move(0,-1)

    # update ship, bound in the square, and check collisions
    for i,j in self._get_bins_idxs(self.player):
      for b in xrange(len(self.bins[i][j])-1,-1,-1):
        if self.bins[i][j][b].collides(self.player):
          if isinstance(self.bins[i][j][b], Baddie) or (
             isinstance(self.bins[i][j][b], Bullet)):
            self.player.hit()
            self._remove_baddie(self.bins[i][j][b])
            break
          elif isinstance(self.bins[i][j][b], Upgrade):
            self.bins[i][j][b].apply(self.player)
            self._remove_baddie(self.bins[i][j][b])
          else:
            assert False, "Unrecognized type: %s" % \
                    str(type(self.bins[i][j][b]))
      if self.player.exploding: break

    # update bullets and delete when O.O.B.
    for b1 in xrange(len(self.bullets)-1,-1,-1):
      self.bullets[b1].tick()
      pos = self.bullets[b1].pos
      w,h = self.size
      if pos[0] < 0 or pos[1] < 0 or pos[0] > w or pos[1] > h:
        del self.bullets[b1]
      else:
        removed = False
        for i,j in self._get_bins_idxs(self.bullets[b1]):
          for b2 in xrange(len(self.bins[i][j])-1,-1,-1):
            Stats.get_stats().inc("comparisons")
            if not isinstance(self.bins[i][j][b2], Upgrade) and \
               self.bins[i][j][b2].collides(self.bullets[b1]):
              if isinstance(self.bins[i][j][b2], Baddie):
                for u in self.bins[i][j][b2].upgrade():
                  self.baddies.append(u)
              self.player.score += self.bins[i][j][b2].score
              self._remove_bullet(self.bullets[b1])
              self._remove_baddie(self.bins[i][j][b2])
              removed = True
              break
          if removed: break

  def _get_simple_bins_idxs(self, obj):
    pos = ( float(obj.pos[0]) / self.size[0] * self.cols,
            float(obj.pos[1]) / self.size[1] * self.rows )
    bin_i = int(pos[0])
    bin_j = int(pos[1])
    i_pos = pos[0] - bin_i
    j_pos = pos[1] - bin_j

    if bin_i < 0:
      bin_i = 0
    elif bin_i >= self.cols:
      bin_i = self.cols - 1
    if bin_j < 0:
      bin_j = 0
    elif bin_j >= self.rows:
      bin_j = self.rows - 1

    return bin_i,bin_j

  def _get_bins_idxs(self, obj):
    pos = ( float(obj.pos[0]) / self.size[0] * self.cols,
            float(obj.pos[1]) / self.size[1] * self.rows )
    bin_i = int(pos[0])
    bin_j = int(pos[1])
    i_pos = pos[0] - bin_i
    j_pos = pos[1] - bin_j

    skip_col_ovrlp = skip_row_ovrlp = False
    if bin_i < 0:
      bin_i = 0
      skip_col_ovrlp = True
    elif bin_i >= self.cols:
      bin_i = self.cols - 1
      skip_col_ovrlp = True
    if bin_j < 0:
      bin_j = 0
      skip_row_ovrlp = True
    elif bin_j >= self.rows:
      bin_j = self.rows - 1
      skip_row_ovrlp = True

    l_bin = r_bin = False
    bins = [(bin_i, bin_j)]
    if not skip_col_ovrlp:
      if i_pos < self.BUFSIZE:
        if bin_i > 0:
          l_bin = True
          bins.append((bin_i-1, bin_j))
      elif i_pos > 1 - self.BUFSIZE:
        if bin_i < self.cols - 1:
          r_bin = True
          bins.append((bin_i+1, bin_j))

    if not skip_row_ovrlp:
      if j_pos < self.BUFSIZE:
        if bin_j > 0:
          bins.append((bin_i, bin_j-1))
          if l_bin:
            bins.append((bin_i-1, bin_j-1))
          elif r_bin:
            bins.append((bin_i+1, bin_j-1))
      elif j_pos > 1 - self.BUFSIZE:
        if bin_j < self.rows - 1:
          bins.append((bin_i, bin_j))
          if l_bin:
            bins.append((bin_i-1, bin_j+1))
          elif r_bin:
            bins.append((bin_i+1, bin_j+1))

    return bins

  def _insert_baddie(self, b):
    i,j = self._get_simple_bins_idxs(b)
    self.bins[i][j].append(b)

  def _remove_bullet(self, b):
    self.bullets.remove(b)

  def _remove_baddie(self, b, idxs = None):
    if idxs is None:
      idxs = self._get_simple_bins_idxs(b)
    self.bins[idxs[0]][idxs[1]].remove(b)
    self.baddies.remove(b)

  def add(self, obj):
    if isinstance(obj, Bullet):
      if obj.side is 'good':
        self.bullets.append(obj)
      else:
        self.baddies.append(obj)
    elif isinstance(obj, Baddie):
      self.baddies.append(obj)
    else:
      print 'Unrecognized type in CollisionSpace.add():', type(obj)

  def draw(self):
    #for x in xrange(self.BINSIZE, self.size[0], self.BINSIZE):
    #  pygame.draw.line(Main.get_main().screen, (0,0,255), (x,0), (x,self.size[1]), 1)
    #for y in xrange(self.BINSIZE, self.size[1], self.BINSIZE):
    #  pygame.draw.line(Main.get_main().screen, (0,0,255), (0,y), (self.size[0],y), 1)
    for b in self.baddies: b.draw()
    for b in self.bullets: b.draw()



################################################################################
#                                   Upgrades                                   #
################################################################################

class Upgrade(object):
  def __init__(self, screen, pos):
    self.screen = screen
    self.pos = list(pos)
    self.color = ( random.randrange(256),
                   random.randrange(256),
                   random.randrange(256) )
    self.traj = random.randrange(200) * math.pi / 100
    self.rect = None

  def move(self, *delta):
    '''Moves the upgrade by the specified change.

    Args:
      delta, (int,int): The change in (X,Y) to move the upgrade by.
    '''
    assert len(delta) == 2, 'Expected 2 arguments.'
    self.rect = None
    self.pos[0] += delta[0]
    self.pos[1] += delta[1]
    return self.pos

  def collides(self, obj):
    if isinstance(obj, Player):
      return self._build_rect().colliderect(obj._build_rect())
    return False

  def _build_rect(self):
    if self.rect is None:
      self.rect = Rect(self.pos[0] - 10, self.pos[1] - 10, 20, 20)
    return self.rect

  def apply(self, player):
    assert False, "Unimplemented upgrade!"

  def tick(self):
    self.rect = None
    self.pos[0] += math.cos(self.traj)
    self.pos[1] += math.sin(self.traj)

  def _draw_one(self, rect):
    pygame.draw.rect(self.screen, self.color, rect, 1)
    pygame.draw.rect(self.screen, self.color + (80,), rect)

  def draw(self):
    '''Just draws the common outline.'''
    self.color = ( (self.color[0] + random.randrange(-2, 2)) % 256,
                   (self.color[1] + random.randrange(-2, 2)) % 256,
                   (self.color[2] + random.randrange(-2, 2)) % 256 )
    self._draw_one(pygame.Rect(self.pos[0] -10, self.pos[1] - 5,  2, 10))
    self._draw_one(pygame.Rect(self.pos[0] + 8, self.pos[1] - 5,  2, 10))
    self._draw_one(pygame.Rect(self.pos[0] - 5, self.pos[1] -10, 10,  2))
    self._draw_one(pygame.Rect(self.pos[0] - 5, self.pos[1] + 8, 10,  2))

class BulletUpgrade(Upgrade):
  def apply(self, player):
    player.gun.power += 1

  def draw(self):
    Upgrade.draw(self)
    pygame.draw.line(self.screen, (255,0,0),
        (self.pos[0], self.pos[1] - 5),
        (self.pos[0], self.pos[1] + 5))
    pygame.draw.line(self.screen, (255,0,0),
        (self.pos[0] - 3, self.pos[1] - 6),
        (self.pos[0] - 1, self.pos[1] + 4))
    pygame.draw.line(self.screen, (255,0,0),
        (self.pos[0] + 3, self.pos[1] - 6),
        (self.pos[0] + 1, self.pos[1] + 4))

class SpeedUpgrade(Upgrade):
  def apply(self, player):
    player.speed += 1

  def draw(self):
    Upgrade.draw(self)
    pygame.draw.lines(self.screen, (255,0,0), False,
        [ (self.pos[0] - 5, self.pos[1] - 5),
          (self.pos[0], self.pos[1]),
          (self.pos[0] - 5, self.pos[1] + 5) ] )
    pygame.draw.lines(self.screen, (255,0,0), False,
        [ (self.pos[0], self.pos[1] - 5),
          (self.pos[0] + 5, self.pos[1]),
          (self.pos[0], self.pos[1] + 5) ] )

class ShieldUpgrade(Upgrade):
  def apply(self, player):
    player.shields += 1

  def draw(self):
    Upgrade.draw(self)
    pygame.draw.circle(self.screen, (255,0,0), map(int, self.pos), 5, 1)



################################################################################
#                                     Main                                     #
################################################################################

class Main(object):
  def __init__(self, options):
    assert self.MAIN_OBJECT is None, "Another Main object is being created!"

    pygame.init()

    self.size = self.width, self.height = options.size
    self.screen = pygame.display.set_mode(self.size, HWSURFACE | DOUBLEBUF)
    self.stats = Stats.get_stats(self.screen, self.size)

    self.player = Player.spawn_at(self.screen, self.width/2, self.height/2)

    self.paused = False
    self.winner = False

    self.fps_timer = pygame.time.Clock()
    self.fps = options.fps
    self.min_fps = options.min_fps
    assert self.min_fps <= self.fps, "min FPS larger than FPS: %d > %d" % (
        self.min_fps, self.fps)

    # fonts
    self.score_font = pygame.font.SysFont('courier', 25, bold = True)
    self.debug_font = pygame.font.SysFont('arial', 8)
    self.gameover_font = pygame.font.SysFont('arial', 18, bold = True)
    self.gameover_pos = self.gameover_font.size('GAME OVER')
    self.gameover_pos = ((self.width - self.gameover_pos[0]) / 2,
                         (self.height - self.gameover_pos[1]) / 2
    self.winner_font = pygame.font.SysFont('arial', 18, bold = True)
    self.winner_pos = self.winner_font.size('WINNER')
    self.winner_pos = ((self.width - self.winner_pos[0]) / 2,
                       (self.height - self.winner_pos[1]) / 2
    self.pause_font = pygame.font.SysFont('arial', 18, bold = True)
    self.pause_pos = self.pause_font.size('Pause')
    self.pause_pos = ((self.width - self.pause_pos[0]) / 2,
                      (self.height - self.pause_pos[1]) / 2

    self.space = CollisionSpace(self.size, self.player)
    self.user_input = Input(self.player, self.space)

    dw, dh = .1 * self.width, .1 * self.height
    self.spawn_points = [
        SpawnPoint(self.screen, self.size, 0, 0, self.space.baddies),
        SpawnPoint(self.screen, self.size,
                0, self.height, self.space.baddies),
        SpawnPoint(self.screen, self.size,
                self.width, 0, self.space.baddies),
        SpawnPoint(self.screen, self.size,
                self.width, self.height, self.space.baddies) ]

    self.lev_i = 0
    self.levels = [Level(self.screen, self.size, self.spawn_points,
                         "Level 1", [(2e3, 0, Wiggler, 20),
                                     (2e3, 1, Wiggler, 20),
                                     (2e3, 2, Wiggler, 20),
                                     (2e3, 3, Wiggler, 20)]),
                   Level(self.screen, self.size, self.spawn_points,
                         "Level 2", [(2e3, 0, FastWiggler, 20),
                                     (2e3, 1, FastWiggler, 20),
                                     (2e3, 2, FastWiggler, 20),
                                     (2e3, 3, FastWiggler, 20)]),
                   Level(self.screen, self.size, self.spawn_points,
                         "Level 3", [(2e3, 0, Homer, 20),
                                     (2e3, 1, Homer, 20),
                                     (2e3, 2, Homer, 20),
                                     (2e3, 3, Homer, 20)]),
                   Level(self.screen, self.size, self.spawn_points,
                         "Level 4", [(2e3, 0, Shooter, 20),
                                     (2e3, 1, Shooter, 20),
                                     (2e3, 2, Shooter, 20),
                                     (2e3, 3, Shooter, 20)]),
                   Level(self.screen, self.size, self.spawn_points,
                         "Level 5", [(2e3, 0, Wiggler, 20),
                                     (2e3, 1, Homer,   20),
                                     (2e3, 2, Wiggler, 20),
                                     (2e3, 3, Homer,   20),
                                     (1e4, 1, Homer,   20),
                                     (1e4, 2, Wiggler, 20),
                                     (1e4, 1, Homer,   20),
                                     (1e4, 2, Wiggler, 20)]),
                   Level(self.screen, self.size, self.spawn_points,
                         "Level 6", [(2e3, 0, Wiggler,     100),
                                     (2e3, 1, Wiggler,     100),
                                     (2e3, 2, Wiggler,     100),
                                     (2e3, 3, Wiggler,     100),
                                     (2e4, 2, Shooter,     100),
                                     (2e4, 2, Shooter,     100),
                                     (2e4, 2, Homer,       100),
                                     (4e4, 3, Homer,       100),
                                     (2e4, 2, FastWiggler, 100),
                                     (4e4, 3, FastWiggler, 100)])]

  def tick(self):
    # Movement
    if self.player.exploding:
      # explode and restart
      if self.player.expl_prog >= 30:
        for s in self.spawn_points: s.clear()
        self.player.reset()
        self.player.pos = [ self.width / 2, self.height / 2 ]
        self.space.empty()
        self.lev_i = 0
        self.levels[self.lev_i].start()
    else:
      self.user_input.tick()


    ########################################################################
    #                          Level Progression                           #
    ########################################################################

    if self.lev_i < len(self.levels) and self.no_more_baddies():
      if self.levels[self.lev_i].done():
        self.lev_i += 1
        if self.lev_i < len(self.levels):
          self.levels[self.lev_i].start()
        else:
          self.winner = True
      else:
        self.levels[self.lev_i].jump_to_next_wave()
    elif not self.winner:
      self.levels[self.lev_i].tick()

    self.space.tick()
    #for b in self.baddies: b.tick()
    #for b in self.bullets: b.tick()
    for s in self.spawn_points: s.tick()


  def run(self):
    '''Runs the game's main loop.'''
    self.levels[self.lev_i].start()
    while True:
      self.stats.reset()

      self.fps_timer.tick(self.fps)
      if self.lev_i < len(self.levels):
        if self.levels[self.lev_i].paused:
          if self.fps_timer.get_fps() >= self.min_fps:
            self.levels[self.lev_i].resume()
        else:
          if self.fps_timer.get_fps() < self.min_fps:
            self.levels[self.lev_i].pause()


      ####################################################################
      #                            User Input                            #
      ####################################################################

      # Quitting and special keys.
      for event in pygame.event.get([pygame.QUIT, pygame.KEYUP]):
        if event.type == pygame.QUIT:
          sys.exit()
        if event.type == pygame.KEYUP:
          if ((event.key == pygame.K_q or event.key == pygame.K_w) and
              (event.mod == pygame.K_RCTRL or event.mod == pygame.K_LCTRL)):
            sys.exit()
          elif event.key == pygame.K_F7:
            random.choice(self.spawn_points).spawn()
          elif event.key == pygame.K_RIGHTBRACKET:
            self.player.gun.power += 1
          elif event.key == pygame.K_LEFTBRACKET:
            if self.player.gun.power > 0:
              self.player.gun.power -= 1
          elif event.key == pygame.K_0:
            self.player.shields += 1
          elif event.key == pygame.K_9:
            if self.player.shields > 0:
              self.player.shields -= 1
          elif event.key == pygame.K_p:
            self.paused = not self.paused
          elif event.key == pygame.K_F6:
            print 'stats:'
            print '  Num Baddies:', len(self.space.baddies)
            print '  Num Bullets:', len(self.space.bullets)
      pygame.event.clear()

      if not self.paused: self.tick()



      ####################################################################
      #                         Drawing Process                          #
      ####################################################################

      self.screen.fill((0,0,0))

      for s in self.spawn_points: s.draw()

      self.space.draw()

      if self.lev_i < len(self.levels):
        self.levels[self.lev_i].draw()

      if self.winner:
        self.screen.blit(self.winner_font.render("WINNER", False,
            (255,255,255)), self.winner_pos)
      elif self.player.exploding:
        self.screen.blit(self.gameover_font.render("GAME OVER", False,
            (255,255,255)), self.gameover_pos)
      elif self.paused:
        self.screen.blit(self.pause_font.render("Paused", False,
            (255,255,255)), self.pause_pos)
      self.screen.blit(self.score_font.render('%d' % self.player.score,
          False, (255,255,255)), (10,10))
      #self.screen.blit(self.score_font.render('{:,}'.format(self.score),
      #    False, (255,255,255)), (10,10))

      self.player.draw()
      self.stats.counts['FPS'] = self.fps_timer.get_fps()
      self.stats.draw()
      pygame.display.flip()

  def spawn_points_empty(self):
    for sp in self.spawn_points:
      if len(sp.queue) != 0:
        return False
    return True

  def no_more_baddies(self):
    return self.spawn_points_empty() and len(self.space.baddies) <= 0

  # singleton enforcement ... and acts as a global variable
  MAIN_OBJECT = None
  @classmethod
  def get_main(cls, options=None):
    if cls.MAIN_OBJECT is None:
      cls.MAIN_OBJECT = cls(options)
    elif options is not None:
      assert len(args) > 0, "cls object already created and arguments passed!"
    return cls.MAIN_OBJECT


def parse_args():
  '''Parses the command line arguments and returns an option object.'''
  ap = argparse.ArgumentParser()
  ap.set_defaults(size='800x600', fps=30, min_fps=25)

  #ap.add_argument('-C', '--config', help="Use a different config file.")
  #ap.add_argument('-j', '--input', dest='input_type',
  #                type='choice', choices=('none','keyboard','joystick'),
  #                help="Force use of the joystick.")
  ap.add_argument('-s', '--size', type=str,
                  help="Set the window resolution.")
  ap.add_argument('-f', '--fps', type=int,
                  help="Set the frame rate.")
  ap.add_argument('-m', '--min-fps', type=int,
                  help="Set the minimum frame rate.")
  args = ap.parse_args()

  try:
    args.size = map(int, args.size.split('x'))
  except ValueError:
    ap.error('Invalid size parameter: "%s"' % args.size)
  finally:
    if len(args.size) != 2:
      ap.error('Invalid size parameter: "%s"' % 'x'.join(args.size))

  if args.min_fps > args.fps:
    print 'Warning! min_fps:%d > fps:%d' % (args.min_fps, args.fps)
    args.min_fps = args.fps

  return args


if __name__ == '__main__':
  Main.get_main(parse_args()).run()
