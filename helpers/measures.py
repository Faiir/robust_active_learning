import numpy as np
from sklearn.metrics import f1_score,roc_auc_score, roc_curve
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt


def f1(true_labels, predictions, average="macro"):
    predicted_labels = np.argmax(predictions, axis=1).flatten()
    f1score = f1_score(true_labels, predicted_labels, average=average)
    return f1score


def accuracy(true_labels, predictions):
    predicted_labels = np.argmax(predictions, axis=1).flatten()
    return 100 * np.mean(predicted_labels == (true_labels.flatten()))


def auroc(iD_Prob, source_labels, writer, oracle_step, plot_auc= True, name=None):
    """
    Computes the ROC score and plots the ROC_AUC curve. 
    Inputs:
        iD_Prob - Probability (or Score) of pool samples being iD
        source_labels - pool labels (1: iD, 0: OoD)
        writer - tensorboard writer
        oracle_step
        plot_auc - flag to plot the curves
    """

    
    if len(iD_Prob.shape)==1:
        iD_Prob = iD_Prob[...,np.newaxis]
    
    
    scaler = MinMaxScaler()
    perdictions = scaler.fit_transform(iD_Prob)
    score = roc_auc_score(source_labels, perdictions)

    if score<0.499:
        print('INFO ----- ROC function requires iD_Prob, not OoD_Prob')
        return auroc(-iD_Prob, source_labels, writer, oracle_step)
   
    if plot_auc:
        fpr, tpr, _ = roc_curve(source_labels, perdictions)
        fig = plt.figure()
        lw = 1
        plt.plot(
            fpr,
            tpr,
            color="red",
            lw=lw,
            label="ROC curve (area = %0.2f)" % score,
        )
        plt.plot([0, 1], [0, 1], color="navy", lw=lw, linestyle="--")
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title("ROC")
        plt.legend(loc="lower right")
        if name is None:
            writer.add_figure(tag=f"AUROC_{oracle_step}", figure=fig)
        else:
            writer.add_figure(tag=f"AUROC_{name}_{oracle_step}", figure=fig)

    return score