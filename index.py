# ========================================================================
# Image Viewer Prototype with Python
# Poldracklab
# ========================================================================
# Copyright 2015 Poldracklab
#

from urllib2 import Request, urlopen, HTTPError
from flask import Flask, render_template
from nilearn.image import resample_img
import numpy
import random
import pandas
import nibabel
import urllib
import json
import os

app = Flask(__name__)

# Validate coordinates
def check_coords(image_data,newx,newy,newz,oldx,oldy,oldz):
    if newx not in range(1,image_data.shape[0]+1):
        newx = oldx
    if newy not in range(1,image_data.shape[1]+1):
        newy = oldy
    if newz not in range(1,image_data.shape[2]+1):
        newz = oldz
    return newx,newy,newz

# Convert 3d slices (nonzero voxels) into melted data frame
def melt(slices):
    df = pandas.DataFrame(columns=["x","y","value","view"])
    df_list = []
    count = 0

    # We need to translate each view by some amount
    translate = [250,750,1150]
    for s in range(len(slices)):
        tmp = df.copy()
        slice = slices[s]
        idx = numpy.where(slice!=0)
        tmp.x = (idx[0] * 4) + translate[s]
        tmp.y = -1*(idx[1] * 4) + 500 # -1 is needed to render brains right side up
        tmp.value = slice[idx[0],idx[1]]
        tmp.view = s
        df_list.append(tmp)
    df = pandas.concat(df_list)
    df.index = range(0,df.shape[0])
    return df

def slice_image(image_data,coords):
    x,y,z = coords
    slicex = image_data.get_data()[x,:,:]
    slicey = image_data.get_data()[:,y,:]
    slicez = image_data.get_data()[:,:,z]
    return slicex,slicey,slicez

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

    # We will slice the image in the middle
    x,y,z = [x/2 for x in image_data.shape]
    slices = slice_image(image_data,[x,y,z])

    # Get coordinates and values for nonzero voxels
    df = melt(slices)    

    # Min and max for each of x and y
    minx = df.x.min()
    miny = df.y.min()
    maxx = df.x.max()
    maxy = df.y.max()

    # Get ranges for color rendering
    minval = image_data.get_data().min()
    maxval = image_data.get_data().max()

    os.remove(savename)
    # Make several transformations of the image
    #dimensions = [2,4,6,8]
    #transforms = [resample_img(image_data,target_affine=numpy.diag([d,d,d])) for d in dimensions]

    return render_template('viewer.html',data=str(df.to_json(orient='records')),
                                         minx=minx,miny=miny,maxx=maxx,maxy=maxy,
                                         minval=minval,
                                         maxval=maxval,
                                         image_id=image_id,
                                         x=x,y=y,z=z)

@app.route('/<image_id>/<oldx>/<oldy>/<oldz>/<x>/<y>/<z>')
def render_slice(image_id,oldx,oldy,oldz,x,y,z):

    x=int(x); y=int(y); z=int(z)
    image = get_json(image_id)   
    filename = os.path.basename(image['file'])
    savename = "tmp/%s.nii.gz" %(image_id)
    if not os.path.exists(savename):
        urllib.urlretrieve(image['file'],savename)
    image_data = nibabel.load(savename)
    
    # Validate coordinates and slice image
    x,y,z = check_coords(image_data,x,y,z,oldx,oldy,oldz)
    slices = slice_image(image_data,[x,y,z])

    # Get coordinates and values for nonzero voxels
    df = melt(slices)    

    # Min and max for each of x and y
    minx = df.x.min()
    miny = df.y.min()
    maxx = df.x.max()
    maxy = df.y.max()

    # Get ranges for color rendering
    minval = image_data.get_data().min()
    maxval = image_data.get_data().max()

    os.remove(savename)
    # Make several transformations of the image
    #dimensions = [2,4,6,8]
    #transforms = [resample_img(image_data,target_affine=numpy.diag([d,d,d])) for d in dimensions]
    return render_template('viewer.html',data=str(df.to_json(orient='records')),
                                         minx=minx,miny=miny,maxx=maxx,maxy=maxy,
                                         minval=minval,
                                         maxval=maxval,
                                         image_id=image_id,
                                         x=x,y=y,z=z)

if __name__ == '__main__':
    app.debug = True
    app.run()
