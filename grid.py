# ========================================================================
# Image Grid Viewer Prototype with Python
# Poldracklab
# ========================================================================
# Copyright 2015 Poldracklab
#

from urllib2 import Request, urlopen, HTTPError
from flask import Flask, render_template
import numpy
import random
import pandas
import nibabel
import urllib
import json
import os

app = Flask(__name__)

# Convert 3d slices (nonzero voxels) into melted data frame
def melt(slices,direction):
    df = pandas.DataFrame(columns=["x","y","value","slice"])
    df_list = []
    count = 0

    # We need to translate each view by some amount
    xtranslate = 10
    ytranslate = 200
    if direction == "z":
        xamount = 125
        yamount = 150
        rownum = 13
    else: 
        xamount = 150
        yamount = 100
        rownum = 11

    count = 1
    for s in range(len(slices)):
        tmp = df.copy()
        slice = slices[s]
        idx = numpy.where(slice!=0)
        tmp.x = (idx[0] * 1.5) + xtranslate
        tmp.y = -1*(idx[1] * 1.5) + ytranslate # -1 is needed to render brains right side up
        tmp.value = slice[idx[0],idx[1]]
        tmp.slice = s
        if count == rownum:
            count = 1
            xtranslate = 10
            ytranslate = ytranslate + yamount
        else:
            count = count + 1
            xtranslate = xtranslate + xamount
        df_list.append(tmp)

    df = pandas.concat(df_list)
    df.index = range(0,df.shape[0])
    return df

def slice_image(image_data,direction="z"):
    slices = []
    if direction == "z":
        slices = [image_data.get_data()[:,:,z] for z in range(image_data.shape[2])]
    elif direction == "y":
        slices = [image_data.get_data()[:,y,:] for y in range(image_data.shape[1])]
    else:
        slices = [image_data.get_data()[x,:,:] for x in range(image_data.shape[0])]  
    return slices

# Convert python series into comma separated string
def listize(series):
    return ",".join([str(x) for x in series.tolist()])

def get_neurovault_images():
    nv = api.NeuroVault()
    df = nv.get_images_with_collections_df()
    image_ids = df.image_id
    image_ids.to_pickle("static/data/neurovault-images.pkl")    

# Functions to get neurovault json result

def get_url(url):
    request = Request(url)
    response = urlopen(request)
    return response.read()

def get_json(image_id):
    url = "http://neurovault.org/api/images/%s" %(image_id)
    json_single = get_url(url)
    return json.loads(json_single.decode("utf-8"))


def render_grid(image_data,image_id,direction,savename):

    # We will slice the image in the middle
    slices = slice_image(image_data,direction)

    # Get coordinates and values for nonzero voxels
    df = melt(slices,direction)    

    # Get standard image, melt equivalently
    #standard = nibabel.load("static/data/MNI152_T1_2mm.nii.gz")
    #standard_slices = slice_image(standard,[x,y,z])
    #standard_df = melt(standard_slices)

    # Min and max for each of x and y
    minx = df.x.min()
    miny = df.y.min()
    maxx = df.x.max()
    maxy = df.y.max()

    # Get ranges for color rendering
    minval = image_data.get_data().min()
    maxval = image_data.get_data().max()

    os.remove(savename)

    return render_template('grid.html',data=str(df.to_json(orient='records')),
                                         minx=minx,miny=miny,maxx=maxx,maxy=maxy,
                                         minval=minval,
                                         maxval=maxval,
                                         image_id=image_id)


@app.route('/')
def init_image():

    # If we don't have the neurovault-id file, create it
    if not os.path.exists('static/data/neurovault-images.pkl'):
        get_neurovault_images()

    # Read in file with ids of public images, select random sample
    image_ids = pandas.read_pickle('static/data/neurovault-images.pkl')
    image_id = random.sample(image_ids.tolist(),1)[0]

    # Retrieve image with neurovault API
    image = get_json(image_id)   
    filename = os.path.basename(image['file'])
    savename = "tmp/%s.nii.gz" %(image_id)
    if not os.path.exists(savename):
        urllib.urlretrieve(image['file'],savename)

    image_data = nibabel.load(savename)
    return render_grid(image_data,image_id,"z",savename)

@app.route('/<image_id>/<direction>')
def render_slice(image_id,direction):

    image = get_json(image_id)   
    filename = os.path.basename(image['file'])
    savename = "tmp/%s.nii.gz" %(image_id)
    if not os.path.exists(savename):
        urllib.urlretrieve(image['file'],savename)
    image_data = nibabel.load(savename)
    return render_grid(image_data,image_id,direction,savename)

if __name__ == '__main__':
    app.debug = True
    app.run()
