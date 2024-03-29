import seaborn
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from torch import nn


def _transform(x):
    if x > 0:
        return 1
    else:
        return -1


def density_plot(pert_preds, gs, hs, targets, writer, oracle_step):
    """density_plot [plots the density of the predicted distribution via entropy and g values ]

    [extended_summary]

    Args:
        pert_preds ([array]): [description]
        gs ([array]): [description]
        hs ([arry]): [description]
        targets ([array]): [description]
        writer ([torch.SummaryWriter]): [description]
        oracle_step ([current AL iteration]): [description]
    """
    targets = np.concatenate(targets, axis=0)
    pert_preds = np.concatenate(pert_preds, axis=0)
    gs = np.concatenate(gs, axis=0)
    hs = np.concatenate(hs, axis=0)

    source = np.array([_transform(xi) for xi in np.array(targets)])
    entropies = -np.sum(pert_preds * np.log(pert_preds), axis=1)
    df_perturbed = pd.DataFrame(
        np.concatenate(
            [
                targets[..., np.newaxis],
                entropies[..., np.newaxis],
                source[..., np.newaxis],
                gs,
                np.max(hs, axis=1, keepdims=True),
            ],
            axis=1,
        ),
        columns=["labels", "entropies", "source", "g_s", "h_s"],
    )
    map_labels = {-1: "OoD"}
    map_labels.update({ii: f"In_dist{ii}" for ii in range(10)})
    source_labels = {-1: "OoD", 1: "InDist"}

    df_perturbed["source_names"] = df_perturbed.source.astype(int).map(source_labels)
    df_perturbed["g_s*e"] = df_perturbed["g_s"] * df_perturbed["entropies"]
    # fig, ax = plt.subplots(1, 1, figsize=(8, 8))

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(6, 18))
    try:
        plot = seaborn.kdeplot(
            data=df_perturbed,
            x="g_s",
            y="entropies",
            hue="source_names",
            fill=False,
            ax=ax1,
        )
    except:
        print("Can't produce KDE, working on scatter plot instead")
        plot = seaborn.scatterplot(
            data=df_perturbed,
            x="g_s",
            y="entropies",
            hue="source_names",
            alpha=0.5,
            ax=ax1,
        )
    try:
        plot = seaborn.kdeplot(
            data=df_perturbed,
            x="g_s",
            y="g_s*e",
            hue="source_names",
            fill=False,
            ax=ax2,
        )
    except IndexError:
        print("Can't produce KDE, working on scatter plot instead")
        plot = seaborn.scatterplot(
            data=df_perturbed,
            x="g_s",
            y="g_s*e",
            hue="source_names",
            alpha=0.5,
            ax=ax2,
        )
    seaborn.histplot(
        data=df_perturbed,
        x="g_s",
        hue="source_names",
        ax=ax3,
    )
    writer.add_figure(tag=f"density_oracle_step_{oracle_step}", figure=fig)
# for c,predictions_perturbed in enumerate(pretubed_preds):
#   print(f"visualization after step {(c+1)*5}")
#   labels = np.concatenate([CIFAR_train_labels,10+CIFAR_test_labels,-np.ones_like(MNIST_test_labels,dtype=np.int8)])
#   print(labels.shape)
#   source = np.concatenate([np.zeros_like(CIFAR_train_labels),np.ones_like(CIFAR_test_labels),-np.ones_like(MNIST_test_labels,dtype=np.int8)])
#   print(source.shape)
#   entropies = -np.sum(predictions_perturbed[0]*np.log(predictions_perturbed[0]+1e-9),axis=1)
#   print(entropies.shape)
#   g_s = predictions_perturbed[2]
#   h_s = predictions_perturbed[3]
#   print(g_s.shape)
#   print(np.max(h_s,axis=1,keepdims=True).shape)
#   df_perturbed = pd.DataFrame(np.concatenate([labels[...,np.newaxis],entropies[...,np.newaxis],source[...,np.newaxis],g_s,np.max(h_s,axis=1,keepdims=True)],axis=1),columns=['labels','entropies','source','g_s','h_s'])


#   map_labels = {-1:'Mnist'}
#   map_labels.update({ii:f'Trained_{ii}' for ii in range(10)})
#   map_labels.update({ii:f'Untrained_{ii-10}' for ii in range(10,20)})

#   source_labels = {-1:'OoD',0:'Trained_ID',1:'Untrained_ID'}

#   df_perturbed['source_names'] = df_perturbed.source.astype(int).map(source_labels)
#   df_perturbed['label_names'] = df_perturbed.labels.astype(int).map(map_labels)
#   df_perturbed['g_s*e'] = df_perturbed['g_s']*df_perturbed['entropies']

#   fig,ax=plt.subplots(1,1,figsize=(8,8))
#   sns.histplot(data=df_perturbed[df_perturbed['source']!=0],x='g_s',hue='source_names',ax=ax);

#   sns.jointplot(data=df_perturbed[df_perturbed['source']!=0], x="g_s", y="entropies", hue="source_names",height=8,joint_kws={'alpha':0.7});

#   sns.jointplot(data=df_perturbed[df_perturbed['source']!=0], x="g_s", y="entropies", hue="source_names",height=8, kind="kde");

#   print("\n\n\n")