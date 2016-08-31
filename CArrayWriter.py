def writeHeader(file,array_name,payload):
    decl_line = "const unsigned char %s[%d]"%( array_name,len(payload))

    #Write header file
    file.write('#define %s_LEN %d\n'%(array_name.upper(),len(payload)))
    file.write('extern ' + decl_line + ';\n')
    
def writeAsCArray(file, array_name, payload):
    decl_line = "const unsigned char %s[%d]"%( array_name,len(payload))
    # Open main output file
    # Write the opening lines
    file.write(decl_line + '={\n')

    c_on_row = 0

    for c in payload:
        file.write("0x%02X,\t"%ord(c))
        c_on_row+=1
        if(c_on_row == 8):
            c_on_row = 0
            file.write("\n")

    file.write("\n};\n")
