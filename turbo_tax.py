# This deals with all Turbo Tax related things
import datetime


def make_txf(full_orders):
    with open("CryptoTurboTax.txf", "w") as text_file:
        # Write the header
        text_file.write("V042\n")
        text_file.write("ACyrptoTaxes\n")
        text_file.write("D " + datetime.datetime.now().strftime('%m/%d/%Y') + "\n")
        text_file.write("^\n")
        for order in full_orders:
            text_file.write("TD\n")
            text_file.write("N712\n")
            text_file.write("C1\n")
            text_file.write("L1\n")
            text_file.write("P" + order[0] + "\n")
            text_file.write("D" + order[1] + "\n")
            text_file.write("D" + order[2] + "\n")
            text_file.write("$%.2f\n" % order[4])
            text_file.write("$%.2f\n" % order[3])
            text_file.write("^\n")
