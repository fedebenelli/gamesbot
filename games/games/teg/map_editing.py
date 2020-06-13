#!/usr/bin/env python3
import sys
import json
from PIL import Image,ImageFont,ImageDraw

"""
This module checks the countries file and draws a map with each player's army
"""

countries_file = sys.argv[1]
maps_folder = sys.argv[2]
country = sys.argv[3]

with open(countries_file) as f:
    data = json.loads(f.read())[country]

image_file = f'{maps_folder}/{country}.png'
font = ImageFont.truetype('NotoSansMono-Bold.ttf', size = 10)

def write_map(x,y,num_units,province,color):
    draw = ImageDraw.Draw(img)
    draw.ellipse((x-2,y-2,x+20,y+15),fill=color,outline='white')
    draw.text((x+4,y),num_units,font=font,fill='white',outline='white')
    #draw.text((x,y+20),province,font=font,fill='black',outline='white')

img = Image.open(image_file)

for province in data:
    x = int(data[province]['x'])
    y = int(data[province]['y'])
    units = data[province]['units']
    write_map(x,y,units,province,data[province]['owner'])

img.save(maps_folder+'temp_map.png')
