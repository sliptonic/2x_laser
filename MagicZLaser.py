import nc
import iso_modal
import math
import datetime
import time

now = datetime.datetime.now()

class Creator(iso_modal.Creator):
    def __init__(self):
        iso_modal.Creator.__init__(self)
        self.output_block_numbers = False
        self.output_tool_definitions = False
        self.output_g43_on_tool_change_line = True

    def SPACE(self):
        if self.start_of_line == True:
            self.start_of_line = False
            return ''
        else:
            return ' '

    def PROGRAM(self): return None
    def PROGRAM_END(self): return('M02')
    #def TOOL(self): return('')
    def SPINDLE(self, format, speed): return(self.SPACE() + 'S' + (format % speed))        
############################################################################
## Begin Program 


    def program_begin(self, id, comment):
        if (self.useCrc == False):
            self.write( ('(Created with laser post processor ' + str(now.strftime("%Y/%m/%d %H:%M")) + ')' + '\n') )
        else:  
            self.write( ('(Created with laser Cutter Radius Compensation post processor ' + str(now.strftime("%Y/%m/%d %H:%M")) + ')' + '\n') )

        self.write( ('M68 E0 Q90'+ '\n') )
        self.write( ('M65 P0'+ '\n') )
        iso_modal.Creator.program_begin(self, id, comment)

    def RAPID(self): return('G00')
    
    def FEED(self): return('G01')

    def spindle(self, s, clockwise):
        #self.write ('(in my post)' + '\n')
        if s < 0: 
            clockwise = False
            s = abs(s)
        
        self.s = self.SPINDLE(self.FORMAT_ANG(), s)
        if clockwise:
            self.write(self.SPINDLE_CW()+self.SPACE() + self.s+ '\n')                
            #self.write(self.s +  '\n')
            #self.write('G04 P2.0 \n')
                
        else:
            self.write(self.SPINDLE_CCW()+self.SPACE() + self.s + '\n')
            #self.write('G04 P2.0 \n')    
   
    def SPINDLE_CW(self): return('M03')

    def profile(self):
        """Profile routine"""
        self.write( ('(starting profile)' +'\n') )
        pass

    def write_spindle(self):
        #self.write(self.SPACE())
        #self.s.write(self)
        pass

    def tool_change(self, id):
        pass  
nc.creator = Creator()

