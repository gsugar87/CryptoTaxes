import os
from fdfgen import forge_fdf


def makePDF(fifoResult, fname, person, social):
    # Write to the PDF
    # Create the directories if they don't already exist
    if not os.path.exists("FDFs"):
        os.makedirs("FDFs")
    if not os.path.exists("PDFs"):
        os.makedirs("PDFs")

    counter = 0
    fileCounter = 0
    fields = [('topmostSubform[0].Page1[0].f1_1[0]', person),
              ('topmostSubform[0].Page1[0].f1_2[0]', social)]
    fnums = [3+i*8 for i in range(14)]
    lastRow1 = 0
    lastRow2 = 0
    lastRow3 = 0
    lastRow4 = 0
    # loop through all FIFO sales
    for sale in fifoResult:
        counter += 1
        # append to the form
        row = counter
        fnum = fnums[row-1]
        fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum), sale[0]))
        fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum+1), sale[1]))
        fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum+2), sale[2]))
        fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum+3), "%1.2f" % sale[3]))
        fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum+4), "%1.2f" % sale[4]))
        if (sale[3]-sale[4]) < 0:
            fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum + 7),
                           "(%1.2f)" % (sale[4] - sale[3])))
        else:
            fields.append(('topmostSubform[0].Page1[0].Table_Line1[0].Row%d[0].f1_%d[0]' % (row, fnum+7), "%1.2f" % (sale[3]-sale[4])))

        lastRow1 += float("%1.2f" % sale[3])
        lastRow2 += float("%1.2f" % sale[4])
        lastRow3 += 0
        lastRow4 += float("%1.2f" % (sale[3]-sale[4]))

        if row == 14 or sale == fifoResult[-1]:
            fields.append(("topmostSubform[0].Page1[0].f1_115[0]", "%1.2f" % lastRow1))
            fields.append(("topmostSubform[0].Page1[0].f1_116[0]", "%1.2f" % lastRow2))
            if lastRow4 < 0:
                fields.append(("topmostSubform[0].Page1[0].f1_118[0]", "(%1.2f)" % abs(lastRow4)))
            else:
                fields.append(("topmostSubform[0].Page1[0].f1_118[0]", "%1.2f" % lastRow4))
            fields.append(("topmostSubform[0].Page1[0].c1_1[2]", 3))
            # save the file and reset the counter
            fdf = forge_fdf("", fields, [], [], [])
            fdf_file = open("FDFs\\" + fname + "_%03d.fdf" % fileCounter, "w")
            fdf_file.write(fdf)
            fdf_file.close()
            # call PDFTK to make the PDF
            os.system("pdftk f8949.pdf fill_form FDFs\\" + fname + "_%03d.fdf" % fileCounter + " output PDFs\\" +
                      fname + "_%03d.pdf" % fileCounter)
            # delete the FDF
            os.system("del FDFs\\" + fname + "_%03d.fdf" % fileCounter)
            counter = 0
            fileCounter += 1
            fields = []
            lastRow1 = 0
            lastRow2 = 0
            lastRow3 = 0
            lastRow4 = 0
