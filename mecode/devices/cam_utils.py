import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import sys

class camUtils(object):
    def __init__(self,scan,start_x,start_y,pitch_x,pitch_y):
        #self.scan = np.load(scan)
        self.scan = scan
        self.start_x = start_x
        self.start_y = start_y
        self.pitch_x = pitch_x
        self.pitch_y = pitch_y
        self.axis_file_names = ['a','b','c','d','XX','YY','ZZ','UU','AA2','BB2','CC2','DD','xxl','yyl','zzl','uul']
        self.axis_names = ['a','b','c','d','XX','YY','ZZ','UU','AA2','BB2','CC2','DD','xx','yy','zz','uu']

    def free_tables(self):
        msg = ""
        for index, axis in enumerate(self.axis_names):
            msg += "CAMSYNC {} {} 0\nFREECAMTABLE {}\n".format(axis,index+1,index+1)
        return msg

    def load_tables(self):
        msg = ""
        interpolation_mode = 1
        tracking_mode = 1
        sync_mode = 1
        for index in range(len(self.axis_names)):
            msg += 'LOADCAMTABLE Y, {}, {}, {}, {}, "Z:\\User Files\\Rob\\Github\\mecode\\mecode\\cam\\{}_sine.cam" NOWRAP\nCAMSYNC {} {} {}\n'.format(index+1,self.axis_names[index],interpolation_mode,tracking_mode,
                    self.axis_file_names[index],self.axis_names[index],index+1,sync_mode)
        return msg

    def move_all_nozzles(self,position):
        if type(position) == type([]):
            return "G90 G1 a{} b{} c{} d{} XX{} YY{} ZZ{} UU{} AA2{} BB2{} CC2{} DD{} xx{} yy{} zz{} uu{}".format(*position)
        else:
            return "G90 G1 a{} b{} c{} d{} XX{} YY{} ZZ{} UU{} AA2{} BB2{} CC2{} DD{} xx{} yy{} zz{} uu{}".format(*([position]*16))

    def gen_tables(self,x_pos,y_pos,y_length,y_offset,start=True):
        #Create plot to show cam pathes
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        
        num_points = int(np.floor(y_length/self.pitch_y)+2)
        preamble = """Number of Points\t{} 
Master Units\t(PRIMARY) 
Slave Units\t(PRIMARY)
""".format(num_points)
        
        f = dict.fromkeys(self.axis_file_names)
        #offset = 375.620-366.35
        nozzle_spacing = 2.5
        plot_vals = []
        initial_pos = []
        
        for index,axis in enumerate(self.axis_file_names):
            f[axis] = open('cam/{}_sine.cam'.format(axis),'w')
            f[axis].write(preamble)
            count = 1
            axis_plot_vals = []
            for y_val in np.arange(y_pos,y_pos+self.pitch_y+y_length,self.pitch_y):
                x_val = x_pos+index*nozzle_spacing
                z_val = self.retrieve(x_val,y_val)
                f[axis].write('{:04d}\t{:06f}\t{:06f}\n'.format(count,y_val+y_offset,z_val))
                axis_plot_vals.append([x_val,y_val,z_val])
                if count == 1 and start:
                    initial_pos.append(z_val)
                elif count == len(np.arange(y_pos,y_pos+self.pitch_y+y_length,self.pitch_y)) and not start:
                    initial_pos.append(z_val)
                count += 1
            plot_vals.append(axis_plot_vals)
        f[axis].close()

        for index,nozzle in enumerate(np.array(plot_vals)):
            x_vals = nozzle[:,0]
            y_vals = nozzle[:,1]
            z_vals = nozzle[:,2]
            ax.plot(x_vals,y_vals,z_vals,label= self.axis_file_names[index])

        plt.legend()
        plt.title('Generated Camming Profiles')
        plt.show()
        fig.savefig('cam/cam_profiles.png')


        #Verify that the profile looks good (safety check)
        response = raw_input('Continue? (Y/N)\n')
        if response.capitalize() == 'N':
            sys.exit()
        
        #Return intial positions for next step
        return initial_pos

    def retrieve(self,x,y):
        x_index = (x-self.start_x)/self.pitch_x
        y_index = (y-self.start_y)/self.pitch_y

        try:
            if x_index.is_integer() and y_index.is_integer():
                #print "Mode 1"
                return self.scan[int(y_index),int(x_index)]

            elif x_index.is_integer() and not y_index.is_integer():
                #print "Mode 2"
                y_min = np.floor(y_index)
                y_max = np.ceil(y_index)
                return (y_max-y_index)/1*self.scan[int(y_min),int(x_index)]+(y_index-y_min)/1*self.scan[int(y_max),int(x_index)]

            elif y_index.is_integer() and not x_index.is_integer():
                #print "Mode 3"
                x_min = np.floor(x_index)
                x_max = np.ceil(x_index)
                return (x_max-x_index)/1*self.scan[int(y_index),int(x_min)]+(x_index-x_min)/1*self.scan[int(y_index),int(x_max)]
            
            else:
                #print "Mode 4"
                x_min = np.floor(x_index)
                x_max = np.ceil(x_index)
                y_min = np.floor(y_index)
                y_max = np.ceil(y_index)
                points = [(x_min,y_min,self.scan[int(y_min),int(x_min)]),
                         (x_min,y_max,self.scan[int(y_max),int(x_min)]),
                         (x_max,y_min,self.scan[int(y_min),int(x_max)]),
                         (x_max,y_max,self.scan[int(y_max),int(x_max)])]
                return self.bilinear_interpolation(x_index,y_index,points)

        except IndexError:
            print "x: {}\ny: {}\nx_index: {}\ny_index: {}".format(x,y,x_index,y_index)

    def bilinear_interpolation(self,x, y, points):
        '''Interpolate (x,y) from values associated with four points.

        The four points are a list of four triplets:  (x, y, value).
        The four points can be in any order.  They should form a rectangle.

            >>> bilinear_interpolation(12, 5.5,
            ...                        [(10, 4, 100),
            ...                         (20, 4, 200),
            ...                         (10, 6, 150),
            ...                         (20, 6, 300)])
            165.0

        '''
        # See formula at:  http://en.wikipedia.org/wiki/Bilinear_interpolation
        points = sorted(points)               # order points by x, then by y

        try:
            (x1, y1, q11), (_x1, y2, q12), (x2, _y1, q21), (_x2, _y2, q22) = points
        except:
            print points

        if x1 != _x1 or x2 != _x2 or y1 != _y1 or y2 != _y2:
            print points
            print 'x: {}, y: {}'.format(x,y)
            raise ValueError('points do not form a rectangle')


        if not x1 <= x <= x2 or not y1 <= y <= y2:
            print points
            print 'x: {}, y: {}'.format(x,y)
            raise ValueError('(x, y) not within the rectangle')


        return (q11 * (x2 - x) * (y2 - y) +
                q21 * (x - x1) * (y2 - y) +
                q12 * (x2 - x) * (y - y1) +
                q22 * (x - x1) * (y - y1)
               ) / ((x2 - x1) * (y2 - y1) + 0.0)