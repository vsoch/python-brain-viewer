# We want to generate a web interface with a simple grid (multiple slice view) of one image.
# if it's an atlas, it should be colored by the label.

# Idea 1: I want to try making two canvas - one with transparency, and then letting the person overlay one on the other.
# - the first layer will show where the images overlap
# - the second layer will be where image 1 has voxels, image 2 doesn't
# - the third layer will be where image 2 has voxels, image 1 doesn't
# the last layer will be a brain atlas?

# READ IN DATA, APPLY BRAIN MASK, GENERATE VECTORS

import nibabel
import numpy
import pandas
from pybraincompare.mr.datasets import get_mni_atlas, get_pair_images, get_mni_atlas
from pybraincompare.compare.mrutils import get_standard_mask, make_binary_deletion_mask, resample_images_ref
from pybraincompare.compare.maths import calculate_atlas_correlation
from nilearn.masking import apply_mask

image1,image2 = get_pair_images(voxdims=["2","2"])
image1 = nibabel.load(image1)
image2 = nibabel.load(image2)
brain_mask  = nibabel.load(get_standard_mask("FSL"))
atlas = get_mni_atlas("2")["2"]
pdmask = make_binary_deletion_mask([image1,image2])

# Combine the pdmask and the brainmask
mask = numpy.logical_and(pdmask,brain_mask.get_data())
mask = nibabel.nifti1.Nifti1Image(mask,affine=brain_mask.get_affine(),header=brain_mask.get_header())

# Resample images to mask
images_resamp, ref_resamp = resample_images_ref([image1,image2],
                                                mask,
                                                interpolation="continuous")

image1 = images_resamp[0].get_data()
image2 = images_resamp[1].get_data()
# We will save the x and y (which are x and z coordinates) in a data frame
# Right now we will save unique colors for images, in future should save value
# that represents similarity / difference

# In image 2, not in image 1
image2_data = pandas.DataFrame(columns=["x","y","color"])

# In image 1, not in image 2
image1_data = pandas.DataFrame(columns=["x","y","color"])

# In both images
overlap_data = pandas.DataFrame(columns=["x","y","color"])

xdim = image1.shape[0]
ydim = image1.shape[1]
zdim = image1.shape[2]

# Number of slices per row
nslices = 10

# Space between slices?
vertical_space = 2

# Prepare lookup data frames for 2D x and y coordinates
xlookup = numpy.zeros(ydim,xdim*zdim))
ylookup = numpy.zeros((ydim,xdim*zdim))

all_indices = numpy.where(xlookup!=39)
for rownum in range(0,ydim):
    ylookup[rownum,:] = [int(x) for x in range(1,(xdim*zdim)+1)]
    xlookup[rownum,:] = numpy.repeat(rownum,(xdim*zdim))

# We will slice images sagitally, meaning we are parallel to z axis, walk(cut) along x, and always take y in entirety
# x in 2D space is y axis in image space left side of sagittal image
# y in 2D space is z axis in image space (top of sagittal image)
# 3rd dimension (not in 2D space) - x is being cut and shown in the rows (moving across sagital slices)

# -------- 2Dx, imagex ----------->
# -
# 2Dy, imagey

# Make a thresholded image to plot
threshpos = numpy.zeros(image1.shape)
threshneg = numpy.zeros(image1.shape)
threshpos[image1>2.5] = image1[image1>2.5]
threshneg[image1<2.5] = image1[image1<2.5]

# TODO: turn this into a function after tested!
datapos = pandas.DataFrame(columns=["y","x","colors"])
dataneg = pandas.DataFrame(columns=["y","x","colors"])
colorpos = "orange"
colorneg = "blue"
dfindex = 0
yindex = vertical_space # y index is how far down 2d page we are
rowstarts = [x*10 for x in range(0,xdim/nslices)]
for r in range(0,len(rowstarts)):
    
    print "Processing slice %s of %s..." %(r,len(rowstarts))

    # Take 10 slices of x
    rowstart = rowstarts[r]
    if rowstart < xdim:
        row_pos = threshpos[range(rowstart,rowstart+nslices),:,:]
        row_neg = threshneg[range(rowstart,rowstart+nslices),:,:]
    else:
        row_pos = threshpos[range(rowstart,xdim),:,:]
        row_neg = threshneg[range(rowstart,xdim),:,:]
    
    # Piece together (sew together) side to side
    rowpos = numpy.zeros((ydim,xdim*zdim))
    rowneg = numpy.zeros((ydim,xdim*zdim))

    sliceindex = 0
    for slicex in range(0,len(row_pos)):
        rowpos[:,sliceindex:sliceindex+zdim] = row_pos[slicex]
        rowneg[:,sliceindex:sliceindex+zdim] = row_neg[slicex]
        sliceindex = sliceindex+zdim

    # Now add row coordinates with nonzero data to final data frame    
    nonzero_data_pos = numpy.where(rowpos!=0)
    nonzero_data_neg = numpy.where(rowneg!=0)
        
    #xs = xlookup[nonzero_data[0],nonzero_data[1]] + yindex
    #ys = xlookup[nonzero_data[0],nonzero_data[1]] # todo, want to add horizontal break?
    #colors = [color for x in range(0,len(xs))]
    #tmp = pandas.DataFrame()    
    #tmp["x"] = xs
    #tmp["y"] = ys
    #tmp["colors"] = colors
    #data = data.append(tmp)

    # Image 1 data
    for p in range(0,len(nonzero_data_pos[0])): 
        datapos.loc[dfindex] = [nonzero_data_pos[0][p]+yindex,nonzero_data_pos[1][p],colorpos]
        dataneg.loc[dfindex] = [nonzero_data_neg[0][p]+yindex,nonzero_data_neg[1][p],colorneg]
        dfindex = dfindex+1    

    # We are at a new row    
    yindex = yindex + xdim + vertical_space


alldata = datapos.append(dataneg)
alldata.to_csv("data/thresh_data.tsv",sep="\t",index=False)
holder.to_csv("data/thresh_data.tsv",sep="\t",index=False)
# Apply mask to images, get vectors of Z score data
vectors = apply_mask(images_resamp,mask)

# Get atlas vectors
atlas_nii = nibabel.load(atlas.file)
atlas_vector = apply_mask([atlas_nii],mask)[0]
atlas_labels =  ['%s' %(atlas.labels[str(int(x))].label) for x in atlas_vector]
atlas_colors = ['%s' %(atlas.color_lookup[x.replace('"',"")]) for x in atlas_labels]

# Now apply the regional mask
data_table = scatterplot_compare_vector(image_vector1=vectors[0],
                                                     image_vector2=vectors[1],
                                                     image_names=["image1","image2"],
                                                     atlas_vector=atlas_vector,
                                                     atlas_labels=atlas_labels,
                                                     atlas_colors=atlas_colors)
                               
data_table_summary = calculate_atlas_correlation(image_vector1,image_vector2,atlas_vector,atlas_labels,
                                atlas_colors,corr_type="pearson",summary=True)
data_table = calculate_atlas_correlation(image_vector1,image_vector2,atlas_vector,atlas_labels,
                                atlas_colors,corr_type="pearson",summary=False)

# Write data to tsv file, first for all regions
data_table.columns = ["x","y","atlas","label","corr","color"]
data_table_summary.columns = ["labels","corr"]
data_table.to_csv("data/scatterplot_data.tsv",sep="\t",index=False)

# Write data to tsv file, now for individual regions
for region in data_table_summary["labels"]:
  subset = data_table[data_table.label==region]
  subset.to_csv("data/%s_data.tsv" %(region),sep="\t",index=False)


# For later we will need to know the max and min values
