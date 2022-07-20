from __future__ import print_function, division
from optparse import OptionParser
from collections import defaultdict, OrderedDict
import concurrent.futures
import sys
import os
import rhalphalib as rl
import numpy as np
import pickle
import gzip
import json
from coffea import hist, processor
from coffea.util import load, save
from scipy import stats
import ROOT

rl.util.install_roofit_helpers()
rl.ParametericSample.PreferRooParametricHist = False

mass_binning = [
    40,
    50,
    60,
    70,
    80,
    90,
    100,
    120,
    150,
    180,
    240,
    300,
]
recoil_binning_dict = {
    "2018": [250, 310, 370, 470, 590, 3000],
    "2017": [250, 310, 370, 470, 590, 3000],
    "2016": [250, 310, 370, 470, 590, 3000]
}


category_map = {"pass": 1, "fail": 0}

with open("data/hf_systematic.json") as fin:
    hf_systematic = json.load(fin)

def signal_xsecScale(signal, s):

    ### Take xsec values from 2017/18 gridpacks
    xsec = {
        ### 2018 signal, mhs = 50 GeV
        "Mz200_mhs50_Mdm100": 0.06606,
        "Mz200_mhs50_Mdm150": 0.02532,
        "Mz300_mhs50_Mdm100": 1.59,
        "Mz300_mhs50_Mdm150": 0.04397,
        "Mz500_mhs50_Mdm150": 0.9072,
        "Mz500_mhs50_Mdm250": 0.02005,
        "Mz500_mhs50_Mdm500": 0.001501,
        "Mz1000_mhs50_Mdm150": 0.5303,
        "Mz1000_mhs50_Mdm500": 0.003643,
        "Mz1000_mhs50_Mdm1000": 0.00005978,
        "Mz2000_mhs50_Mdm500": 0.02582,
        "Mz2000_mhs50_Mdm1000": 0.0002166,
        "Mz2000_mhs50_Mdm1500": 0.000002193,
        "Mz2500_mhs50_Mdm750": 0.005708,
        "Mz2500_mhs50_Mdm1250": 0.00005828,
        "Mz3000_mhs50_Mdm1000": 0.00135,
        "Mz3000_mhs50_Mdm1500": 0.00001537,

        ### 2018 signal, mhs = 70 GeV
        "Mz200_mhs70_Mdm100": 0.05611,
        "Mz200_mhs70_Mdm150": 0.02137,
        "Mz300_mhs70_Mdm100": 1.35,
        "Mz300_mhs70_Mdm150": 0.03773,
        "Mz500_mhs70_Mdm150": 0.7866,
        "Mz500_mhs70_Mdm250": 0.0176,
        "Mz500_mhs70_Mdm500": 0.001304,
        "Mz1000_mhs70_Mdm150": 0.4872,
        "Mz1000_mhs70_Mdm500": 0.003273,
        "Mz1000_mhs70_Mdm1000": 0.00005328,
        "Mz2000_mhs70_Mdm500": 0.02432,
        "Mz2000_mhs70_Mdm1000": 0.0001971,
        "Mz2000_mhs70_Mdm1500": 0.00000193,
        "Mz2500_mhs70_Mdm750": 0.005344,
        "Mz2500_mhs70_Mdm1250": 0.00005322,
        "Mz3000_mhs70_Mdm1000": 0.001265,
        "Mz3000_mhs70_Mdm1500": 0.00001412,

        ### 2018 signal, mhs = 90 GeV
        "Mz200_mhs90_Mdm100": 0.03795,
        "Mz200_mhs90_Mdm150": 0.01497,
        "Mz300_mhs90_Mdm100": 1.151,
        "Mz300_mhs90_Mdm150": 0.03218,
        "Mz500_mhs90_Mdm150": 0.6832,
        "Mz500_mhs90_Mdm250": 0.01529,
        "Mz500_mhs90_Mdm500": 0.001117,
        "Mz1000_mhs90_Mdm150": 0.4376,
        "Mz1000_mhs90_Mdm500": 0.002921,
        "Mz1000_mhs90_Mdm1000": 0.00004682,
        "Mz2000_mhs90_Mdm500": 0.02272,
        "Mz2000_mhs90_Mdm1000": 0.0001796,
        "Mz2000_mhs90_Mdm1500": 0.000001722,
        "Mz2500_mhs90_Mdm750": 0.005043,
        "Mz2500_mhs90_Mdm1250": 0.00004879,
        "Mz3000_mhs90_Mdm1000": 0.001193,
        "Mz3000_mhs90_Mdm1500": 0.00001292,
    }

    signal["sr"].scale({s:xsec[str(s)]},axis='process')


def template(dictionary, process, systematic, recoil, region, category, read_sumw2=False, bkg=False):
    histogram = None
    if bkg:
        histogram = dictionary[region].integrate("process")
    else:
        histogram = dictionary[region].integrate("process", process)
    nominal, sumw2 = histogram.integrate("systematic", "nominal").values(sumw2=True)[()]
    nominal=nominal[recoil, :, category_map[category]]
    sumw2=sumw2[recoil, :, category_map[category]]
    zerobins = nominal <= 0.
    output = nominal
    if "data" not in systematic:
        if "Z+" in str(process):
            output[zerobins] = 1.
            sumw2[zerobins] = 0.
        elif "W+" in str(process) and "fail" in category:
            output[zerobins] = 1.
            sumw2[zerobins] = 0.
        elif "W+" in str(process) and "pass" in category and recoil<4:
            output[zerobins] = 1.
            sumw2[zerobins] = 0.
        elif "TT" in str(process) and "pass" in category  and recoil<4:
            output[zerobins] = 1.
            sumw2[zerobins] = 0.
        else:
            output[zerobins] = 1e-5
            sumw2[zerobins] = 0.
    if "nominal" not in systematic and "data" not in systematic:
        output = histogram.integrate("systematic", systematic).values()[()][recoil, :, category_map[category]]
        output[zerobins] = 1.
        output[~zerobins] /= nominal[~zerobins]
        output[np.isnan(output)] = 1.
    binning = (
        dictionary[region]
        .integrate("process", process)
        .integrate("systematic", systematic)
        .axis("fjmass")
        .edges()
    )
    if read_sumw2:
        return (output, binning, "fjmass", sumw2)
    return (output, binning, "fjmass")

def remap_histograms(hists):
    data_hists = {}
    bkg_hists = {}
    signal_hists = {}

    process = hist.Cat("process", "Process", sorting="placement")
    cats = ("process",)
    sig_map = OrderedDict()
    bkg_map = OrderedDict()
    data_map = OrderedDict()
    bkg_map["Hbb"] = ("Hbb*",)
    bkg_map["DY+jets"] = ("DY+*",)
    bkg_map["VV"] = (["WW", "WZ", "ZZ"],)
    bkg_map["ST"] = ("ST*",)
    bkg_map["TT"] = ("TT*",)
    bkg_map["W+jets"] = ("W+*",)
    bkg_map["W+HF"] = ("W+HF",)
    bkg_map["W+LF"] = ("W+LF",)
    bkg_map["Z+jets"] = ("Z+*",)
    bkg_map["Z+HF"] = ("Z+HF",)
    bkg_map["Z+LF"] = ("Z+LF",)
    bkg_map["G+jets"] = ("G+*",)
    bkg_map["QCD"] = ("QCD*",)
    data_map["MET"] = ("MET",)
    data_map["SingleElectron"] = ("SingleElectron",)
    data_map["SinglePhoton"] = ("SinglePhoton",)
    data_map["EGamma"] = ("EGamma",)
    for signal in hists['sig']['template'].identifiers('process'):
        if 'mhs' not in str(signal): continue
        sig_map[str(signal)] = (str(signal),)  ## signals

    for key in hists["data"].keys():
        bkg_hists[key] = hists["bkg"][key].group(cats, process, bkg_map)
        signal_hists[key] = hists["sig"][key].group(cats, process, sig_map)
        data_hists[key] = hists["data"][key].group(cats, process, data_map)

    print('initial recoil binning',bkg_hists["template"].axis("recoil").edges())

    bkg_hists["template"] = bkg_hists["template"].rebin(
        "fjmass", hist.Bin("fjmass", "Mass", mass_binning)
    )
    signal_hists["template"] = signal_hists["template"].rebin(
        "fjmass", hist.Bin("fjmass", "Mass", mass_binning)
    )
    data_hists["template"] = data_hists["template"].rebin(
        "fjmass", hist.Bin("fjmass", "Mass", mass_binning)
    )

    bkg_hists["template"] = bkg_hists["template"].rebin(
        "recoil", hist.Bin("recoil", "Recoil", recoil_binning)
    )
    signal_hists["template"] = signal_hists["template"].rebin(
        "recoil", hist.Bin("recoil", "Recoil", recoil_binning)
    )
    data_hists["template"] = data_hists["template"].rebin(
        "recoil", hist.Bin("recoil", "Recoil", recoil_binning)
    )

    hists = {"bkg": bkg_hists, "sig": signal_hists, "data": data_hists}

    return hists

def addBtagSyst(dictionary, recoil, process, region, templ, category):
    btagUp = template(dictionary, process, "btagUp", recoil, region, category)[0]
    btagDown = template(dictionary, process, "btagDown", recoil, region, category)[0]
    templ.setParamEffect(btag, btagUp, btagDown)

def addVJetsSyst(dictionary, recoil, process, region, templ, category):
    def addSyst(dictionary, recoil, process, region, templ, category, syst, string):
        histogram = dictionary[region].integrate("process", process)
        nominal=histogram.integrate("systematic", "nominal").values()[()][recoil, :, category_map[category]]
        up=histogram.integrate("systematic", string+"Up").values()[()][recoil, :, category_map[category]]
        down=histogram.integrate("systematic",string+"Down").values()[()][recoil, :, category_map[category]]
        systUp = np.array( up.sum() / nominal.sum() )
        systUp[np.isnan(systUp)] = 1.
        systUp = systUp.sum()
        templ.setParamEffect(syst, systUp)
    addSyst(dictionary, recoil, process, region, templ, category, ew1, "ew1")
    addSyst(dictionary, recoil, process, region, templ, category, ew2W, "ew2W")
    addSyst(dictionary, recoil, process, region, templ, category, ew2Z, "ew2Z")
    addSyst(dictionary, recoil, process, region, templ, category, ew3W, "ew3W")
    addSyst(dictionary, recoil, process, region, templ, category, ew3Z, "ew3Z")
    addSyst(dictionary, recoil, process, region, templ, category, mix, "mix")
    addSyst(dictionary, recoil, process, region, templ, category, qcd1, "qcd1")
    addSyst(dictionary, recoil, process, region, templ, category, qcd2, "qcd2")
    addSyst(dictionary, recoil, process, region, templ, category, qcd3, "qcd3")

def addBBliteSyst(templ, param, epsilon=0):
    for i in range(templ.observable.nbins):
        if templ._nominal[i] <= 0. or templ._sumw2[i] <= 0.:
            continue
        effect_up = np.ones_like(templ._nominal)
        effect_down = np.ones_like(templ._nominal)
        effect_up[i] = (templ._nominal[i] + np.sqrt(templ._sumw2[i]))/templ._nominal[i]
        effect_down[i] = max((templ._nominal[i] - np.sqrt(templ._sumw2[i]))/templ._nominal[i], epsilon)
        templ.setParamEffect(param[i], effect_up, effect_down)

def model(year, recoil, category, s):

    model_id = year + category + "recoil" + str(recoil)
    print(model_id)
    model = rl.Model(str(s) + model_id)

    ###
    ###
    # Signal region
    ###
    ###

    ch_name = "sr" + model_id
    sr = rl.Channel(ch_name)
    model.addChannel(sr)

    ###
    # Add data distribution to the channel
    ###

    if category == 'pass' and options.sumbkg:
        dataTemplate = template(fake_data, "", "data", recoil, "sr", category, bkg=True)
    else:
        dataTemplate = template(data, "MET", "data", recoil, "sr", category)

    sr.setObservation(dataTemplate)
    nbins = len(dataTemplate[1]) - 1
    param = [None for _ in range(nbins)]
    for i in range(nbins):
        param[i] = rl.NuisanceParameter(ch_name + '_mcstat_bin%i' % i, combinePrior='shape')

    ###
    # Z(->nunu)+jets data-driven model
    ###

    if category == "pass":
        sr_zjetsMC = sr_zjetsMCPass
        sr_zjets = sr_zjetsPass
    else:
        sr_zjetsMC = sr_zjetsMCFail
        sr_zjets = sr_zjetsFail
    sr.addSample(sr_zjets)

    ###
    # W(->lnu)+jets data-driven model
    ###

    if category == "pass":
        sr_wjetsMC = sr_wjetsMCPass
        sr_wjetsTemplate = sr_wjetsMCPassTemplate
        sr_wjets = sr_wjetsPass
        if not (recoil<4): ### W+jets modeled by MC instead of data-driven in the last recoil bin
            sr_wjetsMC = rl.TemplateSample(
                "sr" + model_id + "_wjetsMC",
                rl.Sample.BACKGROUND,
                sr_wjetsTemplate
            )
            sr_wjetsMC.setParamEffect(lumi, nlumi)
            sr_wjetsMC.setParamEffect(trig_met, ntrig_met)
            sr_wjetsMC.setParamEffect(veto_tau, nveto_tau)
            sr_wjetsMC.setParamEffect(wjetsMC_norm, nVjets_norm)
            sr_wjetsMC.setParamEffect(jec, njec)
            addBBliteSyst(sr_wjetsMC, param, epsilon=1e-5) ### replace autoMCStats
            addBtagSyst(background, recoil, "W+jets", "sr", sr_wjetsMC, category)
            addVJetsSyst(background, recoil, "W+jets", "sr", sr_wjetsMC, category)
            sr_wjets = sr_wjetsMC
    else:
        sr_wjetsTemplate = sr_wjetsMCFailTemplate
        sr_wjetsMC = sr_wjetsMCFail
        sr_wjets = sr_wjetsFail

    sr.addSample(sr_wjets)

    ###
    # top-antitop model
    ###

    sr_ttTemplate = template(background, "TT", "nominal", recoil, "sr", category, read_sumw2=True)
    sr_ttMC = rl.TemplateSample(
        "sr" + model_id + "_ttMC",
        rl.Sample.BACKGROUND,
        sr_ttTemplate
    )
    sr_ttMC.setParamEffect(lumi, nlumi)
    sr_ttMC.setParamEffect(trig_met, ntrig_met)
    sr_ttMC.setParamEffect(veto_tau, nveto_tau)
    sr_ttMC.setParamEffect(jec, njec)
    addBtagSyst(background, recoil, "TT", "sr", sr_ttMC, category)

    if category == "pass" and recoil<4:
        sr_ttMC.setParamEffect(tt_norm, nMinor_norm)
        #sr_ttMC.autoMCStats(epsilon=1e-5) ### autoMCStats is used for TransferFactorSample
        sigmascale={
            '2016': 1000,
            '2017': 1000,
            '2018': 1000
        }
        sr_ttObservable = rl.Observable("fjmass", sr_ttTemplate[1])
        sr_ttParameters = np.array(
            [
                rl.IndependentParameter(
                    "sr" + year + "_tt_" + category + "_recoil"+str(recoilbin)+"_mass%d" % i,
                    0,
                    -200,
                    50,
                )
                for i in range(sr_ttObservable.nbins)
            ]
        )
        #sr_ttBinYields = sr_ttTemplate[0] * (1 + (0.8/np.maximum(1., np.sqrt(sr_ttTemplate[0]))))**sr_ttParameters
        #sr_ttBinYields = sr_ttTemplate[0] * (1 + (100./np.maximum(1., np.sqrt(sr_ttTemplate[0]))))**sr_ttParameters
        #sr_ttBinYields = sr_ttTemplate[0] * (1 + (sigmascale[year]/np.maximum(1., np.sqrt(sr_ttTemplate[0]))))**sr_ttParameters
        sr_ttBinYields = np.array([rl.IndependentParameter('tmp', b, 1e-5, sr_ttTemplate[0].max()*2) for b in sr_ttTemplate[0]])

        sr_tt = rl.ParametericSample(
            ch_name + "_tt", rl.Sample.BACKGROUND, sr_ttObservable, sr_ttBinYields
        )
        sr.addSample(sr_tt)
    else: ### TT process modeled by MC
        sr_ttMC.setParamEffect(ttMC_norm, nMinor_norm) ### ttMC should be applied for SR fail
        addBBliteSyst(sr_ttMC, param, epsilon=1e-5) ### replace autoMCStats
        sr.addSample(sr_ttMC)

    ###
    # Other MC-driven processes
    ###

    sr_stTemplate = template(background, "ST", "nominal", recoil, "sr", category, read_sumw2=True)
    sr_st = rl.TemplateSample(ch_name + "_stMC", rl.Sample.BACKGROUND, sr_stTemplate)
    sr_st.setParamEffect(lumi, nlumi)
    sr_st.setParamEffect(trig_met, ntrig_met)
    sr_st.setParamEffect(veto_tau, nveto_tau)
    sr_st.setParamEffect(st_norm, nMinor_norm)
    sr_st.setParamEffect(jec, njec)
    addBBliteSyst(sr_st, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoil, "ST", "sr", sr_st, category)
    sr.addSample(sr_st)

    sr_dyjetsTemplate = template(background, "DY+jets", "nominal", recoil, "sr", category, read_sumw2=True)
    sr_dyjets = rl.TemplateSample(
        ch_name + "_dyjetsMC", rl.Sample.BACKGROUND, sr_dyjetsTemplate
    )
    sr_dyjets.setParamEffect(lumi, nlumi)
    sr_dyjets.setParamEffect(trig_met, ntrig_met)
    sr_dyjets.setParamEffect(veto_tau, nveto_tau)
    sr_dyjets.setParamEffect(zjetsMC_norm, nVjets_norm)
    sr_dyjets.setParamEffect(jec, njec)
    addBBliteSyst(sr_dyjets, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoil, "DY+jets", "sr", sr_dyjets, category)
    addVJetsSyst(background, recoil, "DY+jets", "sr", sr_dyjets, category)
    sr.addSample(sr_dyjets)

    sr_vvTemplate = template(background, "VV", "nominal", recoil, "sr", category, read_sumw2=True)
    sr_vv = rl.TemplateSample(ch_name + "_vvMC", rl.Sample.BACKGROUND, sr_vvTemplate)
    sr_vv.setParamEffect(lumi, nlumi)
    sr_vv.setParamEffect(trig_met, ntrig_met)
    sr_vv.setParamEffect(veto_tau, nveto_tau)
    sr_vv.setParamEffect(vv_norm, nMinor_norm)
    sr_vv.setParamEffect(jec, njec)
    addBBliteSyst(sr_vv, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoil, "VV", "sr", sr_vv, category)
    sr.addSample(sr_vv)

    sr_hbbTemplate = template(background, "Hbb", "nominal", recoil, "sr", category, read_sumw2=True)
    sr_hbb = rl.TemplateSample(ch_name + "_hbbMC", rl.Sample.BACKGROUND, sr_hbbTemplate)
    sr_hbb.setParamEffect(lumi, nlumi)
    sr_hbb.setParamEffect(trig_met, ntrig_met)
    sr_hbb.setParamEffect(veto_tau, nveto_tau)
    sr_hbb.setParamEffect(hbb_norm, nMinor_norm)
    sr_hbb.setParamEffect(jec, njec)
    addBBliteSyst(sr_hbb, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoil, "Hbb", "sr", sr_hbb, category)
    sr.addSample(sr_hbb)

    sr_qcdTemplate = template(background, "QCD", "nominal", recoil, "sr", category, read_sumw2=True)
    sr_qcd = rl.TemplateSample(ch_name + "_qcdMC", rl.Sample.BACKGROUND, sr_qcdTemplate)
    sr_qcd.setParamEffect(lumi, nlumi)
    sr_qcd.setParamEffect(trig_met, ntrig_met)
    sr_qcd.setParamEffect(veto_tau, nveto_tau)
    sr_qcd.setParamEffect(qcdsig_norm, nqcd_norm)
    sr_qcd.setParamEffect(jec, njec)
    addBBliteSyst(sr_qcd, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoil, "QCD", "sr", sr_qcd, category)
    sr.addSample(sr_qcd)

    sr_signalTemplate = template(signal, s, "nominal", recoil, "sr", category)
    sr_signal = rl.TemplateSample(
        ch_name + "_" + str(s), rl.Sample.SIGNAL, sr_signalTemplate
    )
    sr_signal.setParamEffect(lumi, nlumi)
    sr_signal.setParamEffect(trig_met, ntrig_met)
    sr_signal.setParamEffect(veto_tau, nveto_tau)
    sr_signal.setParamEffect(jec, njec)
    addBtagSyst(signal, recoil, str(s), "sr", sr_signal, category)
    sr.addSample(sr_signal)

    ###
    # End of SR
    ###

    if category=="pass" and not (recoil<4):
        return model

    ###
    ###
    # Single muon W control region
    ###
    ###

    ch_name = "wmcr" + model_id
    wmcr = rl.Channel(ch_name)
    model.addChannel(wmcr)

    ###
    # Add data distribution to the channel
    ###

    dataTemplate = template(data, "MET", "data", recoil, "wmcr", category)
    wmcr.setObservation(dataTemplate)
    nbins = len(dataTemplate[1]) - 1
    param = [None for _ in range(nbins)]
    for i in range(nbins):
        param[i] = rl.NuisanceParameter(ch_name + '_mcstat_bin%i' % i, combinePrior='shape')

    ###
    # W(->lnu)+jets data-driven model
    ###

    wmcr_wjetsTemplate = template(background, "W+jets", "nominal", recoil, "wmcr", category, read_sumw2=True)
    wmcr_wjetsMC = rl.TemplateSample(
        "wmcr" + model_id + "_wjetsMC",
        rl.Sample.BACKGROUND,
        wmcr_wjetsTemplate
    )
    wmcr_wjetsMC.setParamEffect(lumi, nlumi)
    wmcr_wjetsMC.setParamEffect(trig_met, ntrig_met)
    wmcr_wjetsMC.setParamEffect(veto_tau, nveto_tau)
    wmcr_wjetsMC.setParamEffect(wjets_norm, nVjets_norm)
    wmcr_wjetsMC.setParamEffect(jec, njec)
    wmcr_wjetsMC.setParamEffect(id_mu, nlepton)
    wmcr_wjetsMC.setParamEffect(iso_mu, nlepton)
    #wmcr_wjetsMC.autoMCStats(epsilon=1e-5) ### autoMCStats is used for TransferFactorSample
    addBtagSyst(background, recoil, "W+jets", "wmcr", wmcr_wjetsMC, category)
    addVJetsSyst(background, recoil, "W+jets", "wmcr", wmcr_wjetsMC, category)

    #### Transfer Factor
    wmcr_wjetsTransferFactor = wmcr_wjetsMC.getExpectation() / sr_wjetsMC.getExpectation()
    wmcr_wjets = rl.TransferFactorSample(ch_name + "_wjets", rl.Sample.BACKGROUND, wmcr_wjetsTransferFactor, sr_wjets)
    wmcr.addSample(wmcr_wjets)

    ###
    # top-antitop model
    ###

    wmcr_ttTemplate = template(background, "TT", "nominal", recoil, "wmcr", category, read_sumw2=True)
    wmcr_ttMC = rl.TemplateSample(
        "wmcr" + model_id + "_ttMC",
        rl.Sample.BACKGROUND,
        wmcr_ttTemplate
    )
    wmcr_ttMC.setParamEffect(lumi, nlumi)
    wmcr_ttMC.setParamEffect(trig_met, ntrig_met)
    wmcr_ttMC.setParamEffect(veto_tau, nveto_tau)
    wmcr_ttMC.setParamEffect(jec, njec)
    wmcr_ttMC.setParamEffect(id_mu, nlepton)
    wmcr_ttMC.setParamEffect(iso_mu, nlepton)
    addBtagSyst(background, recoil, "TT", "wmcr", wmcr_ttMC, category)

    if category == "pass":
        #### Transfer Factor
        wmcr_ttMC.setParamEffect(tt_norm, nMinor_norm)
        #wmcr_ttMC.autoMCStats(epsilon=1e-5) ### autoMCStats is used for TransferFactorSample
        wmcr_ttTransferFactor = wmcr_ttMC.getExpectation() / sr_ttMC.getExpectation()
        wmcr_tt = rl.TransferFactorSample(
            ch_name + "_tt", rl.Sample.BACKGROUND, wmcr_ttTransferFactor, sr_tt
        )
        wmcr.addSample(wmcr_tt)
    else: ### TT process modeled by MC
        wmcr_ttMC.setParamEffect(ttMC_norm, nMinor_norm)
        addBBliteSyst(wmcr_ttMC, param, epsilon=1e-5) ### replace autoMCStats
        wmcr.addSample(wmcr_ttMC)

    ###
    # Other MC-driven processes
    ###

    wmcr_stTemplate = template(background, "ST", "nominal", recoil, "wmcr", category, read_sumw2=True)
    wmcr_st = rl.TemplateSample(
        ch_name + "_stMC", rl.Sample.BACKGROUND, wmcr_stTemplate
        )
    wmcr_st.setParamEffect(lumi, nlumi)
    wmcr_st.setParamEffect(trig_met, ntrig_met)
    wmcr_st.setParamEffect(veto_tau, nveto_tau)
    wmcr_st.setParamEffect(st_norm, nMinor_norm)
    wmcr_st.setParamEffect(jec, njec)
    wmcr_st.setParamEffect(id_mu, nlepton)
    wmcr_st.setParamEffect(iso_mu, nlepton)
    addBBliteSyst(wmcr_st, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "ST", "wmcr", wmcr_st, category)
    wmcr.addSample(wmcr_st)

    wmcr_dyjetsTemplate = template(background, "DY+jets", "nominal", recoil, "wmcr", category, read_sumw2=True)
    wmcr_dyjets = rl.TemplateSample(
        ch_name + "_dyjetsMC", rl.Sample.BACKGROUND, wmcr_dyjetsTemplate
    )
    wmcr_dyjets.setParamEffect(lumi, nlumi)
    wmcr_dyjets.setParamEffect(trig_met, ntrig_met)
    wmcr_dyjets.setParamEffect(veto_tau, nveto_tau)
    wmcr_dyjets.setParamEffect(zjetsMC_norm, nVjets_norm)
    wmcr_dyjets.setParamEffect(jec, njec)
    wmcr_dyjets.setParamEffect(id_mu, nlepton)
    wmcr_dyjets.setParamEffect(iso_mu, nlepton)
    addBBliteSyst(wmcr_dyjets, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "DY+jets", "wmcr", wmcr_dyjets, category)
    addVJetsSyst(background, recoil, "DY+jets", "wmcr", wmcr_dyjets, category)
    wmcr.addSample(wmcr_dyjets)

    wmcr_vvTemplate = template(background, "VV", "nominal", recoil, "wmcr", category, read_sumw2=True)
    wmcr_vv = rl.TemplateSample(
        ch_name + "_vvMC", rl.Sample.BACKGROUND, wmcr_vvTemplate
    )
    wmcr_vv.setParamEffect(lumi, nlumi)
    wmcr_vv.setParamEffect(trig_met, ntrig_met)
    wmcr_vv.setParamEffect(veto_tau, nveto_tau)
    wmcr_vv.setParamEffect(vv_norm, nMinor_norm)
    wmcr_vv.setParamEffect(jec, njec)
    wmcr_vv.setParamEffect(id_mu, nlepton)
    wmcr_vv.setParamEffect(iso_mu, nlepton)
    addBBliteSyst(wmcr_vv, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "VV", "wmcr", wmcr_vv, category)
    wmcr.addSample(wmcr_vv)

    wmcr_hbbTemplate = template(background, "Hbb", "nominal", recoil, "wmcr", category, read_sumw2=True)
    wmcr_hbb = rl.TemplateSample(
        ch_name + "_hbbMC", rl.Sample.BACKGROUND, wmcr_hbbTemplate
    )
    wmcr_hbb.setParamEffect(lumi, nlumi)
    wmcr_hbb.setParamEffect(trig_met, ntrig_met)
    wmcr_hbb.setParamEffect(veto_tau, nveto_tau)
    wmcr_hbb.setParamEffect(hbb_norm, nMinor_norm)
    wmcr_hbb.setParamEffect(jec, njec)
    wmcr_hbb.setParamEffect(id_mu, nlepton)
    wmcr_hbb.setParamEffect(iso_mu, nlepton)
    addBBliteSyst(wmcr_hbb, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "Hbb", "wmcr", wmcr_hbb, category)
    wmcr.addSample(wmcr_hbb)

    wmcr_qcdTemplate = template(background, "QCD", "nominal", recoil, "wmcr", category, read_sumw2=True)
    wmcr_qcd = rl.TemplateSample(
        ch_name + "_qcdMC", rl.Sample.BACKGROUND, wmcr_qcdTemplate
    )
    wmcr_qcd.setParamEffect(lumi, nlumi)
    wmcr_qcd.setParamEffect(trig_met, ntrig_met)
    wmcr_qcd.setParamEffect(veto_tau, nveto_tau)
    wmcr_qcd.setParamEffect(qcdmu_norm, nqcd_norm)
    wmcr_qcd.setParamEffect(jec, njec)
    wmcr_qcd.setParamEffect(id_mu, nlepton)
    wmcr_qcd.setParamEffect(iso_mu, nlepton)
    addBBliteSyst(wmcr_qcd, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "QCD", "wmcr", wmcr_qcd, category)
    wmcr.addSample(wmcr_qcd)

    ###
    # End of single muon W control region
    ###

    ###
    ###
    # Single electron W control region
    ###
    ###

    ch_name = "wecr" + model_id
    wecr = rl.Channel(ch_name)
    model.addChannel(wecr)

    ###
    # Add data distribution to the channel
    ###

    if year == "2018":
        dataTemplate = template(data, "EGamma", "data", recoil, "wecr", category)
    else:
        dataTemplate = template(data, "SingleElectron", "data", recoil, "wecr", category)

    wecr.setObservation(dataTemplate)
    nbins = len(dataTemplate[1]) - 1
    param = [None for _ in range(nbins)]
    for i in range(nbins):
        param[i] = rl.NuisanceParameter(ch_name + '_mcstat_bin%i' % i, combinePrior='shape')

    ###
    # W(->lnu)+jets data-driven model
    ###

    wecr_wjetsTemplate = template(background, "W+jets", "nominal", recoil, "wecr", category, read_sumw2=True)
    wecr_wjetsMC = rl.TemplateSample(
        "wecr" + model_id + "_wjetsMC",
        rl.Sample.BACKGROUND,
        wecr_wjetsTemplate
    )
    wecr_wjetsMC.setParamEffect(lumi, nlumi)
    wecr_wjetsMC.setParamEffect(trig_e, ntrig_e)
    wecr_wjetsMC.setParamEffect(veto_tau, nveto_tau)
    wecr_wjetsMC.setParamEffect(wjets_norm, nVjets_norm)
    wecr_wjetsMC.setParamEffect(jec, njec)
    wecr_wjetsMC.setParamEffect(id_e, nlepton)
    wecr_wjetsMC.setParamEffect(reco_e, nlepton)
    #wecr_wjetsMC.autoMCStats(epsilon=1e-5) ### autoMCStats is used for TransferFactorSample
    addBtagSyst(background, recoil, "W+jets", "wecr", wecr_wjetsMC, category)
    addVJetsSyst(background, recoil, "W+jets", "wecr", wecr_wjetsMC, category)

    #### Transfer Factor
    wecr_wjetsTransferFactor = wecr_wjetsMC.getExpectation() / sr_wjetsMC.getExpectation()
    wecr_wjets = rl.TransferFactorSample(
        ch_name + "_wjets", rl.Sample.BACKGROUND, wecr_wjetsTransferFactor, sr_wjets
    )
    wecr.addSample(wecr_wjets)

    ###
    # top-antitop model
    ###

    wecr_ttTemplate = template(background, "TT", "nominal", recoil, "wecr", category, read_sumw2=True)
    wecr_ttMC = rl.TemplateSample(
        "wecr" + model_id + "_ttMC",
        rl.Sample.BACKGROUND,
        wecr_ttTemplate
    )
    wecr_ttMC.setParamEffect(lumi, nlumi)
    wecr_ttMC.setParamEffect(trig_e, ntrig_e)
    wecr_ttMC.setParamEffect(veto_tau, nveto_tau)
    wecr_ttMC.setParamEffect(jec, njec)
    wecr_ttMC.setParamEffect(id_e, nlepton)
    wecr_ttMC.setParamEffect(reco_e, nlepton)
    addBtagSyst(background, recoil, "TT", "wecr", wecr_ttMC, category)

    if category == "pass":
        #### Transfer Factor
        wecr_ttMC.setParamEffect(tt_norm, nMinor_norm)
        #wecr_ttMC.autoMCStats(epsilon=1e-5) ### autoMCStats is used for transferfactorsample
        wecr_ttTransferFactor = wecr_ttMC.getExpectation() / sr_ttMC.getExpectation()
        wecr_tt = rl.TransferFactorSample(
            ch_name + "_tt", rl.Sample.BACKGROUND, wecr_ttTransferFactor, sr_tt
        )
        wecr.addSample(wecr_tt)
    else: ### TT process modeled by MC
        wecr_ttMC.setParamEffect(ttMC_norm, nMinor_norm)
        addBBliteSyst(wecr_ttMC, param, epsilon=1e-5) ### replace autoMCStats
        wecr.addSample(wecr_ttMC)

    ###
    # Other MC-driven processes
    ###

    wecr_stTemplate = template(background, "ST", "nominal", recoil, "wecr", category, read_sumw2=True)
    wecr_st = rl.TemplateSample(
        ch_name + "_stMC", rl.Sample.BACKGROUND, wecr_stTemplate
    )
    wecr_st.setParamEffect(lumi, nlumi)
    wecr_st.setParamEffect(trig_e, ntrig_e)
    wecr_st.setParamEffect(veto_tau, nveto_tau)
    wecr_st.setParamEffect(st_norm, nMinor_norm)
    wecr_st.setParamEffect(jec, njec)
    wecr_st.setParamEffect(id_e, nlepton)
    wecr_st.setParamEffect(reco_e, nlepton)
    addBBliteSyst(wecr_st, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "ST", "wecr", wecr_st, category)
    wecr.addSample(wecr_st)

    wecr_dyjetsTemplate = template(background, "DY+jets", "nominal", recoil, "wecr", category, read_sumw2=True)
    wecr_dyjets = rl.TemplateSample(
        ch_name + "_dyjetsMC", rl.Sample.BACKGROUND, wecr_dyjetsTemplate
    )
    wecr_dyjets.setParamEffect(lumi, nlumi)
    wecr_dyjets.setParamEffect(trig_e, ntrig_e)
    wecr_dyjets.setParamEffect(veto_tau, nveto_tau)
    wecr_dyjets.setParamEffect(zjetsMC_norm, nVjets_norm)
    wecr_dyjets.setParamEffect(jec, njec)
    wecr_dyjets.setParamEffect(id_e, nlepton)
    wecr_dyjets.setParamEffect(reco_e, nlepton)
    addBBliteSyst(wecr_dyjets, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "DY+jets", "wecr", wecr_dyjets, category)
    addVJetsSyst(background, recoil, "DY+jets", "wecr", wecr_dyjets, category)
    wecr.addSample(wecr_dyjets)

    wecr_vvTemplate = template(background, "VV", "nominal", recoil, "wecr", category, read_sumw2=True)
    wecr_vv = rl.TemplateSample(
        ch_name + "_vvMC", rl.Sample.BACKGROUND, wecr_vvTemplate
    )
    wecr_vv.setParamEffect(lumi, nlumi)
    wecr_vv.setParamEffect(trig_e, ntrig_e)
    wecr_vv.setParamEffect(veto_tau, nveto_tau)
    wecr_vv.setParamEffect(vv_norm, nMinor_norm)
    wecr_vv.setParamEffect(jec, njec)
    wecr_vv.setParamEffect(id_e, nlepton)
    wecr_vv.setParamEffect(reco_e, nlepton)
    addBBliteSyst(wecr_vv, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "VV", "wecr", wecr_vv, category)
    wecr.addSample(wecr_vv)

    wecr_hbbTemplate = template(background, "Hbb", "nominal", recoil, "wecr", category, read_sumw2=True)
    wecr_hbb = rl.TemplateSample(
        ch_name + "_hbbMC", rl.Sample.BACKGROUND, wecr_hbbTemplate
    )
    wecr_hbb.setParamEffect(lumi, nlumi)
    wecr_hbb.setParamEffect(trig_e, ntrig_e)
    wecr_hbb.setParamEffect(veto_tau, nveto_tau)
    wecr_hbb.setParamEffect(hbb_norm, nMinor_norm)
    wecr_hbb.setParamEffect(jec, njec)
    wecr_hbb.setParamEffect(id_e, nlepton)
    wecr_hbb.setParamEffect(reco_e, nlepton)
    addBBliteSyst(wecr_hbb, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "Hbb", "wecr", wecr_hbb, category)
    wecr.addSample(wecr_hbb)

    wecr_qcdTemplate = template(background, "QCD", "nominal", recoil, "wecr", category, read_sumw2=True)
    wecr_qcd = rl.TemplateSample(
        ch_name + "_qcdMC", rl.Sample.BACKGROUND, wecr_qcdTemplate
    )
    wecr_qcd.setParamEffect(lumi, nlumi)
    wecr_qcd.setParamEffect(trig_e, ntrig_e)
    wecr_qcd.setParamEffect(veto_tau, nveto_tau)
    wecr_qcd.setParamEffect(qcde_norm, nqcd_norm)
    wecr_qcd.setParamEffect(jec, njec)
    wecr_qcd.setParamEffect(id_e, nlepton)
    wecr_qcd.setParamEffect(reco_e, nlepton)
    addBBliteSyst(wecr_qcd, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "QCD", "wecr", wecr_qcd, category)
    wecr.addSample(wecr_qcd)

    ###
    # End of single electron W control region
    ###

    if not (category=="pass"):
        return model

    ###
    ###
    # Single muon top control region
    ###
    ###

    ch_name = "tmcr" + model_id
    tmcr = rl.Channel(ch_name)
    model.addChannel(tmcr)

    ###
    # Add data distribution to the channel
    ###

    dataTemplate = template(data, "MET", "data", recoil, "tmcr", category)
    tmcr.setObservation(dataTemplate)
    nbins = len(dataTemplate[1]) - 1
    param = [None for _ in range(nbins)]
    for i in range(nbins):
        param[i] = rl.NuisanceParameter(ch_name + '_mcstat_bin%i' % i, combinePrior='shape')

    ###
    # top-antitop model
    ###

    tmcr_ttTemplate = template(background, "TT", "nominal", recoil, "tmcr", category, read_sumw2=True)
    tmcr_ttMC = rl.TemplateSample(
        "tmcr" + model_id + "_ttMC",
        rl.Sample.BACKGROUND,
        tmcr_ttTemplate
    )
    tmcr_ttMC.setParamEffect(lumi, nlumi)
    tmcr_ttMC.setParamEffect(trig_met, ntrig_met)
    tmcr_ttMC.setParamEffect(veto_tau, nveto_tau)
    tmcr_ttMC.setParamEffect(tt_norm, nMinor_norm)
    tmcr_ttMC.setParamEffect(jec, njec)
    tmcr_ttMC.setParamEffect(id_mu, nlepton)
    tmcr_ttMC.setParamEffect(iso_mu, nlepton)
    #tmcr_ttMC.autoMCStats(epsilon=1e-5) ### autoMCStats is used for TransferFactorSample
    addBtagSyst(background, recoil, "TT", "tmcr", tmcr_ttMC, category)

    #### Transfer Factor
    tmcr_ttTransferFactor = tmcr_ttMC.getExpectation() / sr_ttMC.getExpectation()
    tmcr_tt = rl.TransferFactorSample(
        ch_name + "_tt", rl.Sample.BACKGROUND, tmcr_ttTransferFactor, sr_tt
    )
    tmcr.addSample(tmcr_tt)

    ###
    # Other MC-driven processes
    ###

    tmcr_wjetsTemplate = template(background, "W+jets", "nominal", recoil, "tmcr", category, read_sumw2=True)
    tmcr_wjets = rl.TemplateSample(
        ch_name + "_wjetsMC", rl.Sample.BACKGROUND, tmcr_wjetsTemplate
    )
    tmcr_wjets.setParamEffect(lumi, nlumi)
    tmcr_wjets.setParamEffect(trig_met, ntrig_met)
    tmcr_wjets.setParamEffect(veto_tau, nveto_tau)
    tmcr_wjets.setParamEffect(wjetsMC_norm, nVjets_norm)
    tmcr_wjets.setParamEffect(jec, njec)
    tmcr_wjets.setParamEffect(id_mu, nlepton)
    tmcr_wjets.setParamEffect(iso_mu, nlepton)
    addBBliteSyst(tmcr_wjets, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "W+jets", "tmcr", tmcr_wjets, category)
    addVJetsSyst(background, recoil, "W+jets", "tmcr", tmcr_wjets, category)
    tmcr.addSample(tmcr_wjets)

    tmcr_stTemplate = template(background, "ST", "nominal", recoil, "tmcr", category, read_sumw2=True)
    tmcr_st = rl.TemplateSample(
        ch_name + "_stMC", rl.Sample.BACKGROUND, tmcr_stTemplate
    )
    tmcr_st.setParamEffect(lumi, nlumi)
    tmcr_st.setParamEffect(trig_met, ntrig_met)
    tmcr_st.setParamEffect(veto_tau, nveto_tau)
    tmcr_st.setParamEffect(st_norm, nMinor_norm)
    tmcr_st.setParamEffect(jec, njec)
    tmcr_st.setParamEffect(id_mu, nlepton)
    tmcr_st.setParamEffect(iso_mu, nlepton)
    addBBliteSyst(tmcr_st, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "ST", "tmcr", tmcr_st, category)
    tmcr.addSample(tmcr_st)

    tmcr_dyjetsTemplate = template(background, "DY+jets", "nominal", recoil, "tmcr", category, read_sumw2=True)
    tmcr_dyjets = rl.TemplateSample(
        ch_name + "_dyjetsMC", rl.Sample.BACKGROUND, tmcr_dyjetsTemplate
    )
    tmcr_dyjets.setParamEffect(lumi, nlumi)
    tmcr_dyjets.setParamEffect(trig_met, ntrig_met)
    tmcr_dyjets.setParamEffect(veto_tau, nveto_tau)
    tmcr_dyjets.setParamEffect(zjetsMC_norm, nVjets_norm)
    tmcr_dyjets.setParamEffect(jec, njec)
    tmcr_dyjets.setParamEffect(id_mu, nlepton)
    tmcr_dyjets.setParamEffect(iso_mu, nlepton)
    addBBliteSyst(tmcr_dyjets, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "DY+jets", "tmcr", tmcr_dyjets, category)
    addVJetsSyst(background, recoil, "DY+jets", "tmcr", tmcr_dyjets, category)
    tmcr.addSample(tmcr_dyjets)

    tmcr_vvTemplate = template(background, "VV", "nominal", recoil, "tmcr", category, read_sumw2=True)
    tmcr_vv = rl.TemplateSample(
        ch_name + "_vvMC", rl.Sample.BACKGROUND, tmcr_vvTemplate
    )
    tmcr_vv.setParamEffect(lumi, nlumi)
    tmcr_vv.setParamEffect(trig_met, ntrig_met)
    tmcr_vv.setParamEffect(veto_tau, nveto_tau)
    tmcr_vv.setParamEffect(vv_norm, nMinor_norm)
    tmcr_vv.setParamEffect(jec, njec)
    tmcr_vv.setParamEffect(id_mu, nlepton)
    tmcr_vv.setParamEffect(iso_mu, nlepton)
    addBBliteSyst(tmcr_vv, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "VV", "tmcr", tmcr_vv, category)
    tmcr.addSample(tmcr_vv)

    tmcr_hbbTemplate = template(background, "Hbb", "nominal", recoil, "tmcr", category, read_sumw2=True)
    tmcr_hbb = rl.TemplateSample(
        ch_name + "_hbbMC", rl.Sample.BACKGROUND, tmcr_hbbTemplate
    )
    tmcr_hbb.setParamEffect(lumi, nlumi)
    tmcr_hbb.setParamEffect(trig_met, ntrig_met)
    tmcr_hbb.setParamEffect(veto_tau, nveto_tau)
    tmcr_hbb.setParamEffect(hbb_norm, nMinor_norm)
    tmcr_hbb.setParamEffect(jec, njec)
    tmcr_hbb.setParamEffect(id_mu, nlepton)
    tmcr_hbb.setParamEffect(iso_mu, nlepton)
    addBBliteSyst(tmcr_hbb, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "Hbb", "tmcr", tmcr_hbb, category)
    tmcr.addSample(tmcr_hbb)

    tmcr_qcdTemplate = template(background, "QCD", "nominal", recoil, "tmcr", category, read_sumw2=True)
    tmcr_qcd = rl.TemplateSample(
        ch_name + "_qcdMC", rl.Sample.BACKGROUND, tmcr_qcdTemplate
    )
    tmcr_qcd.setParamEffect(lumi, nlumi)
    tmcr_qcd.setParamEffect(trig_met, ntrig_met)
    tmcr_qcd.setParamEffect(veto_tau, nveto_tau)
    tmcr_qcd.setParamEffect(qcdmu_norm, nqcd_norm)
    tmcr_qcd.setParamEffect(jec, njec)
    tmcr_qcd.setParamEffect(id_mu, nlepton)
    tmcr_qcd.setParamEffect(iso_mu, nlepton)
    addBBliteSyst(tmcr_qcd, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "QCD", "tmcr", tmcr_qcd, category)
    tmcr.addSample(tmcr_qcd)

    ###
    # End of single muon top control region
    ###

    ###
    ###
    # Single electron top control region
    ###
    ###

    ch_name = "tecr" + model_id
    tecr = rl.Channel(ch_name)
    model.addChannel(tecr)

    ###
    # Add data distribution to the channel
    ###

    if year == "2018":
        dataTemplate = template(data, "EGamma", "data", recoil, "tecr", category)
    else:
        dataTemplate = template(data, "SingleElectron", "data", recoil, "tecr", category)

    tecr.setObservation(dataTemplate)
    nbins = len(dataTemplate[1]) - 1
    param = [None for _ in range(nbins)]
    for i in range(nbins):
        param[i] = rl.NuisanceParameter(ch_name + '_mcstat_bin%i' % i, combinePrior='shape')

    ###
    # top-antitop model
    ###

    tecr_ttTemplate = template(background, "TT", "nominal", recoil, "tecr", category, read_sumw2=True)
    tecr_ttMC = rl.TemplateSample(
        "tecr" + model_id + "_ttMC",
        rl.Sample.BACKGROUND,
        tecr_ttTemplate
    )
    tecr_ttMC.setParamEffect(lumi, nlumi)
    tecr_ttMC.setParamEffect(trig_e, ntrig_e)
    tecr_ttMC.setParamEffect(veto_tau, nveto_tau)
    tecr_ttMC.setParamEffect(tt_norm, nMinor_norm)
    tecr_ttMC.setParamEffect(jec, njec)
    tecr_ttMC.setParamEffect(id_e, nlepton)
    tecr_ttMC.setParamEffect(reco_e, nlepton)
    #tecr_ttMC.autoMCStats(epsilon=1e-5) ### autoMCStats is used for TransferFactorSample
    addBtagSyst(background, recoil, "TT", "tecr", tecr_ttMC, category)

    #### Transfer Factor
    tecr_ttTransferFactor = tecr_ttMC.getExpectation() / sr_ttMC.getExpectation()
    tecr_tt = rl.TransferFactorSample(
        ch_name + "_tt", rl.Sample.BACKGROUND, tecr_ttTransferFactor, sr_tt
    )
    tecr.addSample(tecr_tt)

    ###
    # Other MC-driven processes
    ###

    tecr_wjetsTemplate = template(background, "W+jets", "nominal", recoil, "tecr", category, read_sumw2=True)
    tecr_wjets = rl.TemplateSample(
        ch_name + "_wjetsMC", rl.Sample.BACKGROUND, tecr_wjetsTemplate
    )
    tecr_wjets.setParamEffect(lumi, nlumi)
    tecr_wjets.setParamEffect(trig_e, ntrig_e)
    tecr_wjets.setParamEffect(veto_tau, nveto_tau)
    tecr_wjets.setParamEffect(wjetsMC_norm, nVjets_norm)
    tecr_wjets.setParamEffect(jec, njec)
    tecr_wjets.setParamEffect(id_e, nlepton)
    tecr_wjets.setParamEffect(reco_e, nlepton)
    addBBliteSyst(tecr_wjets, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "W+jets", "tecr", tecr_wjets, category)
    addVJetsSyst(background, recoil, "W+jets", "tecr", tecr_wjets, category)
    tecr.addSample(tecr_wjets)

    tecr_stTemplate = template(background, "ST", "nominal", recoil, "tecr", category, read_sumw2=True)
    tecr_st = rl.TemplateSample(
        ch_name + "_stMC", rl.Sample.BACKGROUND, tecr_stTemplate
    )
    tecr_st.setParamEffect(lumi, nlumi)
    tecr_st.setParamEffect(trig_e, ntrig_e)
    tecr_st.setParamEffect(veto_tau, nveto_tau)
    tecr_st.setParamEffect(st_norm, nMinor_norm)
    tecr_st.setParamEffect(jec, njec)
    tecr_st.setParamEffect(id_e, nlepton)
    tecr_st.setParamEffect(reco_e, nlepton)
    addBBliteSyst(tecr_st, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "ST", "tecr", tecr_st, category)
    tecr.addSample(tecr_st)

    tecr_dyjetsTemplate = template(background, "DY+jets", "nominal", recoil, "tecr", category, read_sumw2=True)
    tecr_dyjets = rl.TemplateSample(
        ch_name + "_dyjetsMC", rl.Sample.BACKGROUND, tecr_dyjetsTemplate
    )
    tecr_dyjets.setParamEffect(lumi, nlumi)
    tecr_dyjets.setParamEffect(trig_e, ntrig_e)
    tecr_dyjets.setParamEffect(veto_tau, nveto_tau)
    tecr_dyjets.setParamEffect(zjetsMC_norm, nVjets_norm)
    tecr_dyjets.setParamEffect(jec, njec)
    tecr_dyjets.setParamEffect(id_e, nlepton)
    tecr_dyjets.setParamEffect(reco_e, nlepton)
    addBBliteSyst(tecr_dyjets, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "DY+jets", "tecr", tecr_dyjets, category)
    addVJetsSyst(background, recoil, "DY+jets", "tecr", tecr_dyjets, category)
    tecr.addSample(tecr_dyjets)

    tecr_vvTemplate = template(background, "VV", "nominal", recoil, "tecr", category, read_sumw2=True)
    tecr_vv = rl.TemplateSample(
        ch_name + "_vvMC", rl.Sample.BACKGROUND, tecr_vvTemplate
    )
    tecr_vv.setParamEffect(lumi, nlumi)
    tecr_vv.setParamEffect(trig_e, ntrig_e)
    tecr_vv.setParamEffect(veto_tau, nveto_tau)
    tecr_vv.setParamEffect(vv_norm, nMinor_norm)
    tecr_vv.setParamEffect(jec, njec)
    tecr_vv.setParamEffect(id_e, nlepton)
    tecr_vv.setParamEffect(reco_e, nlepton)
    addBBliteSyst(tecr_vv, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "VV", "tecr", tecr_vv, category)
    tecr.addSample(tecr_vv)

    tecr_hbbTemplate = template(background, "Hbb", "nominal", recoil, "tecr", category, read_sumw2=True)
    tecr_hbb = rl.TemplateSample(
        ch_name + "_hbbMC", rl.Sample.BACKGROUND, tecr_hbbTemplate
    )
    tecr_hbb.setParamEffect(lumi, nlumi)
    tecr_hbb.setParamEffect(trig_e, ntrig_e)
    tecr_hbb.setParamEffect(veto_tau, nveto_tau)
    tecr_hbb.setParamEffect(hbb_norm, nMinor_norm)
    tecr_hbb.setParamEffect(jec, njec)
    tecr_hbb.setParamEffect(id_e, nlepton)
    tecr_hbb.setParamEffect(reco_e, nlepton)
    addBBliteSyst(tecr_hbb, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "Hbb", "tecr", tecr_hbb, category)
    tecr.addSample(tecr_hbb)

    tecr_qcdTemplate = template(background, "QCD", "nominal", recoil, "tecr", category, read_sumw2=True)
    tecr_qcd = rl.TemplateSample(
        ch_name + "_qcdMC", rl.Sample.BACKGROUND, tecr_qcdTemplate
    )
    tecr_qcd.setParamEffect(lumi, nlumi)
    tecr_qcd.setParamEffect(trig_e, ntrig_e)
    tecr_qcd.setParamEffect(veto_tau, nveto_tau)
    tecr_qcd.setParamEffect(qcde_norm, nqcd_norm)
    tecr_qcd.setParamEffect(jec, njec)
    tecr_qcd.setParamEffect(id_e, nlepton)
    tecr_qcd.setParamEffect(reco_e, nlepton)
    addBBliteSyst(tecr_qcd, param, epsilon=1e-5) ### replace autoMCStats
    addBtagSyst(background, recoilbin, "QCD", "tecr", tecr_qcd, category)
    tecr.addSample(tecr_qcd)

    ###
    # End of single electron top control region
    ###

    return model


if __name__ == "__main__":
    if not os.path.exists("datacards"):
        os.mkdir("datacards")
    parser = OptionParser()
    parser.add_option("-y", "--year", help="year", dest="year", default="")
    parser.add_option("-b", "--sumbkg", help="replace data to sum of backgrounds", action="store_true", dest="sumbkg")
    (options, args) = parser.parse_args()
    year = options.year
    recoil_binning = recoil_binning_dict[year]
    recoilbins = np.array(recoil_binning)
    nrecoil = len(recoilbins) - 1

    ###
    # Extract histograms from input file
    ###

    print("Grouping histograms")
    hists = load("hists/darkhiggs" + year + ".scaled")


    ###
    # Prepare fake data (MUST DO BEFORE REMAPPING!!!!)
    ###

    fake_data_hists = hists['bkg']
    fake_data_hists['template'] = fake_data_hists['template'].rebin('fjmass',hist.Bin('fjmass','Mass', mass_binning))
    fake_data_hists['template'] = fake_data_hists['template'].rebin('recoil',hist.Bin('recoil','Recoil',recoil_binning))

    ###
    # Remapping histograms 
    ###

    hists = remap_histograms(hists)
    data_hists = hists["data"]
    bkg_hists = hists["bkg"]
    signal_hists = hists["sig"]

    ###
    # Preparing histograms for fit
    ##

    data = {}
    fake_data = {}

    #### Use real data in CRs + SR fail while fake data in SR pass
    if options.sumbkg:
        fake_data['sr'] = fake_data_hists["template"].integrate("region", 'sr').sum("gentype")
    for r in data_hists["template"].identifiers("region"):
        data[str(r)] = data_hists["template"].integrate("region", r).sum("gentype")

    background = {}
    for r in bkg_hists["template"].identifiers("region"):
        background[str(r)] = bkg_hists["template"].integrate("region", r).sum("gentype")

    signal = {}
    for r in signal_hists["template"].identifiers("region"):
        signal[str(r)] = signal_hists["template"].integrate("region", r).sum("gentype")

    ### 
    # Fill missing signal mass points for 2018
    ###

    if year == '2018':
        print("Grouping missing signal histograms in 2018")
        tmphists = load("hists/signal" + year + ".scaled")
        tmphists = remap_histograms(tmphists)
        signal_tmphists = tmphists['sig']

        for r in signal_hists["template"].identifiers("region"):
            signal[str(r)] += signal_tmphists["template"].integrate("region", r).sum("gentype")


    ###
    ###
    # Setting up systematics
    ###
    ###
    lumi = rl.NuisanceParameter("lumi" + year, "lnN")
    zjets_norm = rl.NuisanceParameter("zjets_norm", "lnN")
    wjets_norm = rl.NuisanceParameter("wjets_norm", "lnN")
    tt_norm = rl.NuisanceParameter("tt_norm", "lnN")
    id_e = rl.NuisanceParameter("id_e" + year, "lnN")
    id_mu = rl.NuisanceParameter("id_mu" + year, "lnN")
    id_pho = rl.NuisanceParameter("id_pho" + year, "lnN")
    reco_e = rl.NuisanceParameter("reco_e" + year, "lnN")
    iso_mu = rl.NuisanceParameter("iso_mu" + year, "lnN")
    trig_e = rl.NuisanceParameter("trig_e" + year, "lnN")
    trig_met = rl.NuisanceParameter("trig_met" + year, "lnN")
    trig_pho = rl.NuisanceParameter("trig_pho" + year, "lnN")
    veto_tau = rl.NuisanceParameter("veto_tau" + year, "lnN")
    jec = rl.NuisanceParameter("jec" + year, "lnN")
    #btag = rl.NuisanceParameter("btag" + year, "shapeN")  # AK4 btag
    btag = rl.NuisanceParameter("btag" + year, "shape")  # AK4 btag
    ew1 = rl.NuisanceParameter("ew1", "lnN")
    #ew2G = rl.NuisanceParameter("ew2G", "lnN")
    ew2W = rl.NuisanceParameter("ew2W", "lnN")
    ew2Z = rl.NuisanceParameter("ew2Z", "lnN")
    #ew3G = rl.NuisanceParameter("ew3G", "lnN")
    ew3W = rl.NuisanceParameter("ew3W", "lnN")
    ew3Z = rl.NuisanceParameter("ew3Z", "lnN")
    mix = rl.NuisanceParameter("mix", "lnN")
    #muF = rl.NuisanceParameter("muF", "lnN")
    #muR = rl.NuisanceParameter("muR", "lnN")
    qcd1 = rl.NuisanceParameter("qcd1", "lnN")
    qcd2 = rl.NuisanceParameter("qcd2", "lnN")
    qcd3 = rl.NuisanceParameter("qcd3", "lnN")
    whf_fraction = rl.NuisanceParameter("whf_fraction", "lnN")
    zhf_fraction = rl.NuisanceParameter("zhf_fraction", "lnN")
    #ghf_fraction = rl.NuisanceParameter("ghf_fraction", "shapeN")

    ###
    # Set lnN or shape numbers
    ###

    nlumi = 1.027
    ntrig_met = 1.02
    ntrig_e = 1.01
    nveto_tau = 1.03
    njec = 1.05
    nlepton = 1.02 ## id_mu, iso_mu, id_e, reco_e
    nVjets_norm = 1.4 ## wjetsMC_norm, wjets_norm, zjetsMC_norm, zjets_norm, whf_fraction, zhf_fraction
    nMinor_norm = 1.2 ## tt_norm, ttMC_norm, st_norm, vv_norm, hbb_norm
    nqcd_norm = 2.0 ## qcdsig_norm, qcde_norm, qcdmu_norm

    ###
    # Preparing Rhalphabet
    ###

    msdbins = np.array(mass_binning)
    msd = rl.Observable('fjmass', msdbins)
    # here we derive these all at once with 2D array
    ptpts, msdpts = np.meshgrid(recoilbins[:-1] + 0.3 * np.diff(recoilbins), msdbins[:-1] + 0.5 * np.diff(msdbins), indexing='ij')
    recoilscaled = (ptpts - 250.) / (3000. - 250.)
    msdscaled = (msdpts - 40.) / (300.0 - 40.)

    tf_dataResidualW = rl.BernsteinPoly("tf_dataResidualW"+year, (0, 1), ['recoil', 'fjmass'], limits=(1e-5, 10))
    tf_dataResidualW_params = tf_dataResidualW(recoilscaled, msdscaled)
    tf_dataResidualZ = rl.BernsteinPoly("tf_dataResidualZ"+year, (0, 1), ['recoil', 'fjmass'], limits=(1e-5, 10))
    tf_dataResidualZ_params = tf_dataResidualZ(recoilscaled, msdscaled)
   
    model_dict = {}
    for recoilbin in range(nrecoil):

        sr_zjetsMCFailTemplate = template(background, "Z+jets", "nominal", recoilbin, "sr", "fail", read_sumw2=True)
        sr_zjetsMCFail = rl.TemplateSample(
            "sr" + year + "fail" + "recoil" + str(recoilbin) + "_zjetsMC",
            rl.Sample.BACKGROUND,
            sr_zjetsMCFailTemplate
        )
        sr_zjetsMCFail.setParamEffect(lumi, nlumi)
        sr_zjetsMCFail.setParamEffect(zjets_norm, nVjets_norm)
        sr_zjetsMCFail.setParamEffect(trig_met, ntrig_met)
        sr_zjetsMCFail.setParamEffect(veto_tau, nveto_tau)
        sr_zjetsMCFail.setParamEffect(jec, njec)
        #sr_zjetsMCFail.autoMCStats(epsilon=1e-5) ### autoMCStats is used for TransferFactorSample
        addBtagSyst(background, recoilbin, "Z+jets", "sr", sr_zjetsMCFail, "fail")
        addVJetsSyst(background, recoilbin, "Z+jets", "sr", sr_zjetsMCFail, "fail")

        sr_zjetsObservable = rl.Observable("fjmass", sr_zjetsMCFailTemplate[1])
        sr_zjetsParameters = np.array(
            [
                rl.IndependentParameter(
                    "sr" + year + "_zjets_fail_recoil"+str(recoilbin)+"_mass%d" % i,
                    0,
                    -25,
                    25,
                )
                for i in range(sr_zjetsObservable.nbins)
            ]
        )
        sr_zjetsBinYields = np.array([rl.IndependentParameter('tmp', b, 1e-5, sr_zjetsMCFailTemplate[0].max()*2) for b in sr_zjetsMCFailTemplate[0]])

        sr_zjetsFail = rl.ParametericSample(
            "sr" + year + "fail" + "recoil" + str(recoilbin)+ "_zjets",
            rl.Sample.BACKGROUND,
            sr_zjetsObservable,
            sr_zjetsBinYields
        )

        sr_wjetsMCFailTemplate = template(background, "W+jets", "nominal", recoilbin, "sr", "fail", read_sumw2=True)
        sr_wjetsMCFail = rl.TemplateSample(
            "sr" + year + "fail" + "recoil" + str(recoilbin) + "_wjetsMC",
            rl.Sample.BACKGROUND,
            sr_wjetsMCFailTemplate
        )
        sr_wjetsMCFail.setParamEffect(lumi, nlumi)
        sr_wjetsMCFail.setParamEffect(wjets_norm, nVjets_norm)
        sr_wjetsMCFail.setParamEffect(trig_met, ntrig_met)
        sr_wjetsMCFail.setParamEffect(veto_tau, nveto_tau)
        sr_wjetsMCFail.setParamEffect(jec, njec)
        #sr_wjetsMCFail.autoMCStats(epsilon=1e-5) ### autoMCStats is used for TransferFactorSample
        addBtagSyst(background, recoilbin, "W+jets", "sr", sr_wjetsMCFail, "fail")
        addVJetsSyst(background, recoilbin, "W+jets", "sr", sr_wjetsMCFail, "fail")

        sr_wjetsFailTransferFactor = sr_wjetsMCFail.getExpectation() / sr_zjetsMCFail.getExpectation()
        sr_wjetsFail = rl.TransferFactorSample(
            "sr" + year + "fail" + "recoil" + str(recoilbin)+ "_wjets",
            rl.Sample.BACKGROUND,
            sr_wjetsFailTransferFactor,
            sr_zjetsFail
        )

        sr_zjetsMCPassTemplate = template(background, "Z+jets", "nominal", recoilbin, "sr", "pass", read_sumw2=True)
        sr_zjetsMCPass = rl.TemplateSample(
            "sr" + year + "pass" + "recoil" + str(recoilbin) + "_zjetsMC",
            rl.Sample.BACKGROUND,
            sr_zjetsMCPassTemplate
        )
        sr_zjetsMCPass.setParamEffect(lumi, nlumi)
        sr_zjetsMCPass.setParamEffect(zjets_norm, nVjets_norm)
        sr_zjetsMCPass.setParamEffect(trig_met, ntrig_met)
        sr_zjetsMCPass.setParamEffect(veto_tau, nveto_tau)
        sr_zjetsMCPass.setParamEffect(jec, njec)
        #sr_zjetsMCPass.autoMCStats(epsilon=1e-5) ### autoMCStats is used for TransferFactorSample
        addBtagSyst(background, recoilbin, "Z+jets", "sr", sr_zjetsMCPass, "pass")
        addVJetsSyst(background, recoilbin, "Z+jets", "sr", sr_zjetsMCPass, "pass")

        tf_paramsZdeco = sr_zjetsMCPassTemplate[0] / sr_zjetsMCFailTemplate[0]
        tf_paramsZ = tf_paramsZdeco * tf_dataResidualZ_params[recoilbin, :]

        sr_zjetsPass = rl.TransferFactorSample(
            "sr" + year + "pass" + "recoil" + str(recoilbin)+ "_zjets",
            rl.Sample.BACKGROUND,
            tf_paramsZ,
            sr_zjetsFail
        )

        sr_wjetsMCPassTemplate = template(background, "W+jets", "nominal", recoilbin, "sr", "pass", read_sumw2=True)
        sr_wjetsMCPass = rl.TemplateSample(
            "sr" + year + "pass" + "recoil" + str(recoilbin) + "_wjetsMC",
            rl.Sample.BACKGROUND,
            sr_wjetsMCPassTemplate
        )
        sr_wjetsMCPass.setParamEffect(lumi, nlumi)
        sr_wjetsMCPass.setParamEffect(wjets_norm, nVjets_norm)
        sr_wjetsMCPass.setParamEffect(trig_met, ntrig_met)
        sr_wjetsMCPass.setParamEffect(veto_tau, nveto_tau)
        sr_wjetsMCPass.setParamEffect(jec, njec)
        #sr_wjetsMCPass.autoMCStats(epsilon=1e-5) ### autoMCStats is used for TransferFactorSample
        addBtagSyst(background, recoilbin, "W+jets", "sr", sr_wjetsMCPass, "pass")
        addVJetsSyst(background, recoilbin, "W+jets", "sr", sr_wjetsMCPass, "pass")

        tf_paramsWdeco = sr_wjetsMCPassTemplate[0] / sr_wjetsMCFailTemplate[0]
        tf_paramsW = tf_paramsWdeco * tf_dataResidualW_params[recoilbin, :]

        sr_wjetsPass = rl.TransferFactorSample(
            "sr" + year + "pass" + "recoil" + str(recoilbin)+ "_wjets",
            rl.Sample.BACKGROUND,
            tf_paramsW,
            sr_wjetsFail
        )

        for s in signal["sr"].identifiers("process"):
            print("Signal is:", str(s))
            signal_xsecScale(signal, s) ## scale signal yields by its cross section
            for category in ["pass", "fail"]:
                qcdpho_norm = rl.NuisanceParameter("qcdpho_norm" + year + category, "lnN")
                qcde_norm = rl.NuisanceParameter("qcde_norm" + year + category, "lnN")
                qcdmu_norm = rl.NuisanceParameter("qcdmu_norm" + year + category, "lnN")
                qcdsig_norm = rl.NuisanceParameter("qcdsig_norm" + year + category, "lnN")
                st_norm = rl.NuisanceParameter("st_norm" + year + category, "lnN")
                ttMC_norm = rl.NuisanceParameter("tt_norm" + year + category, "lnN")
                vv_norm = rl.NuisanceParameter("vv_norm" + year + category, "lnN")
                hbb_norm = rl.NuisanceParameter("hbb_norm" + year + category, "lnN")
                wjetsMC_norm = rl.NuisanceParameter("wjets_norm" + year + category, "lnN")
                zjetsMC_norm = rl.NuisanceParameter("zjets_norm" + year + category, "lnN")

                with open(
                        "data/"
                        + str(s).replace('_','')
                        + "-"
                        + year
                        + "-"
                        + category
                        + "-recoil"
                        + str(recoilbin)
                        + ".model",
                        "wb",
                ) as fout:
                    pickle.dump(model(year, recoilbin, category, s), fout, protocol=2)
