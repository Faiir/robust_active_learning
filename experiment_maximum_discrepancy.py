from typing import Dict, List, Union

""" 

Credit for Code from: https://github.com/Mephisto405/Unsupervised-Out-of-Distribution-Detection-by-Maximum-Classifier-Discrepancy
Paper: https://arxiv.org/pdf/1908.04951v1.pdf 
Title: Unsupervised Out-of-Distribution Detection by Maximum Classifier Discrepancy
Authors: Qing Yu Kiyoharu Aizawa
"""

# python
import datetime
import os
import json
import numpy as np


import pandas as pd

from torch.utils.tensorboard.writer import SummaryWriter


# torch
import torch
import torch.nn as nn
import torch.optim as optim
from torchsummary import summary
import torch.optim.lr_scheduler as lr_scheduler
from .helpers.measures import accuracy, auroc, f1


# project
from .experiment_base import experiment_base
from .model.get_model import get_model
from .helpers.early_stopping import EarlyStopping
from .helpers.plots import get_tsne_plot
from .data.data_manager import Data_manager
from .data.datahandler_for_array import create_dataloader


def verbosity(message, verbose, epoch):
    if verbose == 1:
        if epoch % 10 == 0:
            print(message)
    elif verbose == 2:
        print(message)
    return None


def _create_log_path_al(log_dir: str = ".", OOD_ratio: float = 0.0) -> None:
    current_time = datetime.now().strftime("%H-%M-%S")
    log_file_name = "Experiment-from-" + str(current_time) + ".csv"
    current_time = datetime.now().strftime("%H-%M-%S")
    log_file_name = (
        "Experiment-from-"
        + str(current_time)
        + "-"
        + "stanard-al"
        + "-"
        + str(OOD_ratio)
    )

    log_dir = os.path.join(".", "log_dir")

    if os.path.exists(log_dir) == False:
        os.mkdir(os.path.join(".", "log_dir"))

    log_path = os.path.join(log_dir, log_file_name)

    return log_path


class experiment_maximum_discrepancy(experiment_base):
    def __init__(
        self,
        basic_settings: Dict,
        exp_settings: Dict,
        log_path: str,
        writer: SummaryWriter,
    ) -> None:
        super().__init__(basic_settings, exp_settings, log_path, writer)
        self.log_path = log_path
        self.writer = writer
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        basic_settings.update(exp_settings)
        self.current_experiment = basic_settings

        self.load_settings()

        if self.device == "cuda":
            torch.backends.cudnn.benchmark = True

        self.construct_data_manager()

    # overrides train
    def train(self, train_loader, val_loader, optimizer, criterion, device, **kwargs):
        """train [main training function of the project]

        [extended_summary]

        Args:
            train_loader ([torch.Dataloader]): [dataloader with the training data]
            optimizer ([torch.optim]): [optimizer for the network]
            criterion ([Loss function]): [Pytorch loss function]
            device ([str]): [device to train on cpu/cuda]
            epochs (int, optional): [epochs to run]. Defaults to 5.
            **kwargs (verbose and validation dataloader)
        Returns:
            [tupel(trained network, train_loss )]:
        """
        # verbose = kwargs.get("verbose", 1)

        if self.verbose > 0:
            print("\nTraining with device :", device)
            print("Number of Training Samples : ", len(train_loader.dataset))
            if val_loader is not None:
                print("Number of Validation Samples : ", len(val_loader.dataset))
            print("Number of Epochs : ", self.epochs)

            if self.verbose > 1:
                summary(self.model, input_size=(3, 32, 32))

        lr_sheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            "min",
            factor=0.1,
            patience=int(self.epochs * 0.05),
            min_lr=1e-7,
            verbose=True,
        )

        validation = True
        if kwargs.get("patience", None) is None:
            print(
                f"INFO ------ Early Stopping Patience not specified using {int(self.epochs * 0.1)}"
            )
        patience = kwargs.get("patience", int(self.epochs * 0.1))
        early_stopping = EarlyStopping(patience, verbose=True, delta=1e-6)

        for epoch in range(1, self.epochs + 1):
            if self.verbose > 0:
                print(f"\nEpoch: {epoch}")

            train_loss = 0
            train_acc = 0
            correct_1 = 0
            correct_2 = 0
            total = 0
            for batch_idx, (data, target) in enumerate(train_loader):
                if len(data) > 1:
                    self.model.train()
                    data, target = data.to(device).float(), target.to(device).long()

                    optimizer.zero_grad(set_to_none=True)
                    # yhat = self.model(data).to(device)
                    out_1, out_2 = self.model(data)
                    out_1.to(device)
                    out_2.to(device)
                    loss = self.criterion(out_1, target) + self.criterion(out_2, target)
                    # loss = criterion(yhat, target)
                    try:
                        train_loss += loss.item()
                    except:
                        print("loss item skipped loss")
                    _, pred_1 = torch.max(out_1.data, 1)
                    _, pred_2 = torch.max(out_2.data, 1)
                    total += target.size(0)
                    correct_1 += (pred_1 == target).sum().item()
                    correct_2 += (pred_2 == target).sum().item()
                    # train_acc += torch.sum(torch.argmax(yhat, dim=1) == target).item()

                    loss.backward()
                    optimizer.step()
                else:
                    pass

            avg_train_loss = train_loss / len(train_loader)
            avg_train_acc = ((100 * correct_1 / total) + (100 * correct_2 / total)) / 2
            # avg_train_acc = train_acc / len(train_loader.dataset)

            if epoch % 1 == 0:
                if validation:
                    val_loss = 0
                    val_acc = 0
                    v_correct_1 = 0
                    v_correct_2 = 0

                    self.model.eval()  # prep self.model for evaluation
                    with torch.no_grad():
                        for vdata, vtarget in val_loader:
                            vdata, vtarget = (
                                vdata.to(device).float(),
                                vtarget.to(device).long(),
                            )
                            voutput1, voutput2 = self.model(vdata)
                            vloss = criterion(voutput1, vtarget) + criterion(
                                voutput2, vtarget
                            )
                            val_loss += vloss.item()

                            _, v_pred_1 = torch.max(voutput1.data, 1)
                            _, v_pred_2 = torch.max(voutput2.data, 1)
                            val_acc += vtarget.size(0)
                            v_correct_1 += (v_pred_1 == vtarget).sum().item()
                            v_correct_2 += (v_pred_2 == vtarget).sum().item()
                            # val_acc += torch.sum(
                            #     torch.argmax(voutput1, dim=1) == vtarget
                            # ).item()
                    avg_val_acc = (
                        (100 * v_correct_1 / val_acc) + (100 * v_correct_2 / val_acc)
                    ) / 2
                    avg_val_loss = val_loss / len(self.val_loader)
                    # avg_val_acc = val_acc / len(self.val_loader.dataset)

                    early_stopping(avg_val_loss, self.model)
                    if kwargs.get("lr_sheduler", True):
                        lr_sheduler.step(avg_val_loss)

                    verbosity(
                        f"Val_loss: {avg_val_loss:.4f} Val_acc : {100*avg_val_acc:.2f}",
                        self.verbose,
                        epoch,
                    )

                    if early_stopping.early_stop:
                        print(
                            f"Early stopping epoch {epoch} , avg train_loss {avg_train_loss}, avg val loss {avg_val_loss}"
                        )
                        break

            verbosity(
                f"Train_loss: {avg_train_loss:.4f} Train_acc : {100*avg_train_acc:.2f}",
                self.verbose,
                epoch,
            )

        self.avg_train_loss_hist = avg_train_loss
        self.avg_val_loss_hist = avg_val_loss
        self.avg_train_acc_hist = avg_train_acc
        self.avg_val_loss_hist = avg_val_acc

    # overrides test
    @torch.no_grad()
    def test(self):
        """test [computes loss of the test set]

        [extended_summary]

        Returns:
            [type]: [description]
        """
        test_loss = 0
        test_acc = 0
        total = 0
        correct_1 = 0
        correct_2 = 0
        self.model.eval()
        for (t_data, t_target) in self.test_loader:
            t_data, t_target = (
                t_data.to(self.device).float(),
                t_target.to(self.device).long(),
            )

            t_output1, t_output2 = self.model(t_data)
            t_output1.to(self.device).long()
            t_output2.to(self.device).long()
            # t_output.to(self.device).long()
            t_loss = self.criterion(t_output1, t_target) + self.criterion(
                t_output2, t_target
            )
            test_loss += t_loss
            _, pred_1 = torch.max(t_output1.data, 1)
            _, pred_2 = torch.max(t_output2.data, 1)
            total += t_target.size(0)
            correct_1 += (pred_1 == t_target).sum().item()
            correct_2 += (pred_2 == t_target).sum().item()

            # test_acc += torch.sum(torch.argmax(t_output, dim=1) == t_target).item()
        self.avg_test_acc = ((100 * correct_1 / total) + (100 * correct_2 / total)) / 2
        # self.avg_test_acc = test_acc / len(self.test_loader.dataset)
        self.avg_test_loss = test_loss.to("cpu").detach().numpy() / len(
            self.test_loader
        )  # return avg testloss

    def finetune(self, trainloader, poolloader, num_epochs=10, sheduler=None):
        best_roc = 0.0
        print("Fine-tuning-discrepancy-loss")
        for epoch in range(num_epochs):
            # sheduler.step()
            self.model.train()
            pool_loder_iterator = iter(poolloader)
            # maybe iterate over entire pool?
            optimizer = optim.SGD(
                self.model.parameters(),
                weight_decay=self.weight_decay,
                lr=self.lr,
                momentum=self.momentum,
                nesterov=self.nesterov,
            )
            for batch_idx, (data, target) in enumerate(trainloader):
                unsup_data, _ = next(
                    pool_loder_iterator
                )  # poolloader[batch_idx % len(poolloader.dataset)]
                unsup_data = unsup_data.to(self.device).float()
                data, target = (
                    data.to(self.device).float(),
                    target.to(self.device).long(),
                )
                optimizer.zero_grad()
                out_1, out_2 = self.model(data)
                out_1 = out_1.to(self.device)
                out_2 = out_2.to(self.device)
                loss_sup = self.criterion(out_1, target) + self.criterion(out_2, target)
                u_out_1, u_out_2 = self.model(unsup_data)
                u_out_1 = u_out_1.to(self.device)
                u_out_2 = u_out_2.to(self.device)
                loss_unsup = self.DiscrepancyLoss(u_out_1, u_out_2)
                loss = loss_unsup + loss_sup
                loss.backward()
                optimizer.step() #changing so the same optimizer is given zero grad and then used to updated the model

            # validate skipp for now
            # self.model.eval()
            # labels = torch.zeros((2000, )).cuda() # a big tensor
            # dists = torch.zeros((2000, )).cuda() # discrepancy (or distance)

    # overrides save_settings
    def save_settings(self) -> None:
        log_config_path = os.path.join(self.log_dir + ".json")
        with open(log_config_path, "w") as f:
            json.dump(self.current_experiment, f)

    def save_al_logs(self) -> None:
        log_df = self.data_manager.get_logs()
        al_logs = os.path.join(self.log_path, "log_dir", f"logs-{self.exp_name}.csv")
        with open(al_logs, mode="w", encoding="utf-8") as logfile:
            colums = log_df.columns
            for colum in colums:
                logfile.write(colum + ",")
            logfile.write("\n")
            for _, row in log_df.iterrows():
                for c in colums:
                    logfile.write(str(row[c]))
                    logfile.write(",")
                logfile.write("\n")

    # overrides construct_data_manager
    def construct_data_manager(self) -> None:
        self.data_manager = Data_manager(
            iD_datasets=[self.iD],
            OoD_datasets=self.OoD,
            labelled_size=self.labelled_size,
            pool_size=self.pool_size,
            OoD_ratio=self.OOD_ratio,
            test_iD_size=None,
            subclass=self.current_experiment.get("subclass", {"do_subclass": False}),
        )
        print("initialised data_manager")

    # overrides set_sampler
    def set_sampler(self, sampler) -> None:
        if sampler == "random":
            from .helpers.sampler import random_sample

            self.sampler = random_sample
        elif sampler == "highest-entropy":
            from .helpers.sampler import uncertainity_sampling_highest_entropy

            self.sampler = uncertainity_sampling_highest_entropy
        elif sampler == "least-confidence":
            from .helpers.sampler import uncertainity_sampling_least_confident

            self.sampler = uncertainity_sampling_least_confident
        elif sampler == "extra_class_entropy":
            from .helpers.sampler import extra_class_sampler

            self.sampler = extra_class_sampler(self.extra_class_thresholding)
        elif sampler == "maximum_discrepancy":
            from .helpers.sampler import (
                uncertainity_sampling_highest_entropy_maxium_discrepancy,
            )

            self.sampler = uncertainity_sampling_highest_entropy_maxium_discrepancy

    # overrides set_model
    def set_model(self, model_name) -> None:
        if model_name == "maximum_discrepancy":
            self.model = get_model(
                model_name, num_classes=self.num_classes, maximum_discrepancy=True
            )  # needs rewrite maybe
        else:
            raise NotImplementedError
        self.model.to(self.device)

    # overrides create_plots
    def create_plots(self) -> None:
        tsne_plot = get_tsne_plot(self.data_manager, self.iD, self.model, self.device)
        self.writer.add_figure(
            tag=f"{self.metric}/{self.iD}/{self.experiment_settings.get('oracles', 'oracle')}/tsne",
            figure=tsne_plot,
        )

    def pool_predictions(self, pool_loader) -> Union[np.ndarray, np.ndarray]:
        yhat1 = []
        yhat2 = []
        labels_list = []
        for (data, labels) in pool_loader:
            pred1, pred2 = self.model(data.to(self.device).float(), apply_softmax=True)
            yhat1.append(pred1.to("cpu").detach().numpy())
            yhat2.append(pred2.to("cpu").detach().numpy())
            labels_list.append(labels)
        predictions1 = np.concatenate(yhat1)
        predictions2 = np.concatenate(yhat2)
        labels_list = np.concatenate(labels_list)
        return predictions1, predictions2, labels_list

    def create_dataloader(self) -> None:
        result_tup = create_dataloader(
            self.data_manager,
            self.batch_size,
            self.validation_split,
            validation_source=self.validation_source,
        )
        self.train_loader = result_tup[0]
        self.test_loader = result_tup[1]
        self.pool_loader = result_tup[2]
        self.val_loader = result_tup[3]

    def create_optimizer(self) -> None:
        self.optimizer = optim.SGD(
            self.model.parameters(),
            weight_decay=self.weight_decay,
            lr=self.lr,
            momentum=self.momentum,
            nesterov=self.nesterov,
        )

    def DiscrepancyLoss(self, input_1, input_2, m=1.2):
        soft_1 = nn.functional.softmax(input_1, dim=1)
        soft_2 = nn.functional.softmax(input_2, dim=1)
        entropy_1 = -soft_1 * nn.functional.log_softmax(input_1, dim=1)
        entropy_2 = -soft_2 * nn.functional.log_softmax(input_2, dim=1)
        entropy_1 = torch.sum(entropy_1, dim=1)
        entropy_2 = torch.sum(entropy_2, dim=1)

        loss = torch.nn.ReLU()(m - torch.mean(entropy_1 - entropy_2))
        return loss

    def create_criterion(self) -> None:
        self.criterion = nn.CrossEntropyLoss()
        self.unsup_criterion = self.DiscrepancyLoss

    # overrides load_settings
    def load_settings(self) -> None:
        # active Learning settings
        self.oracle_stepsize = self.current_experiment.get("oracle_stepsize", 100)
        self.oracle_steps = self.current_experiment.get("oracle_steps", 10)
        self.iD = self.current_experiment.get("iD", "Cifar10")
        self.OoD = self.current_experiment.get("OoD", ["Fashion_MNIST"])
        self.labelled_size = self.current_experiment.get("labelled_size", 3000)
        self.pool_size = self.current_experiment.get("pool_size", 50000)
        self.OOD_ratio = self.current_experiment.get("OOD_ratio", 0.0)

        # training settings
        self.epochs = self.current_experiment.get("epochs", 100)
        self.batch_size = self.current_experiment.get("batch_size", 64)
        self.weight_decay = self.current_experiment.get("weight_decay", 1e-4)
        self.metric = self.current_experiment.get("metric", 10)
        self.lr = self.current_experiment.get("lr", 0.1)
        self.nesterov = self.current_experiment.get("nesterov", False)
        self.momentum = self.current_experiment.get("momentum", 0.9)
        self.lr_sheduler = self.current_experiment.get("lr_sheduler", True)
        self.num_classes = self.current_experiment.get("num_classes", 10)
        self.validation_split = self.current_experiment.get("validation_split", 0.3)
        self.validation_source = self.current_experiment.get(
            "validation_source", "test"
        )
        # self.criterion = self.current_experiment.get("criterion", "crossentropy")
        self.create_criterion()
        self.metric = self.current_experiment.get("metric", "accuracy")
        # logging
        self.verbose = self.current_experiment.get("verbose", 1)

        self.thresholding = self.current_experiment.get("thresholding", True)
        print(f'----- THRESHOLDING : {self.thresholding}')
        self.perform_finetune = self.current_experiment.get("finetune", True)
        # _create_log_path_al(self.OOD_ratio)

        self.oracle = self.current_experiment.get("oracle", "maximum_discrepancy")
        self.set_sampler(self.oracle)
        self.exp_name = self.current_experiment.get("exp_name", "maximum_discrepancy")

    # overrides perform_experiment
    def perform_experiment(self):

        self.train_loss_hist = []
        check_path = os.path.join(
            self.log_path, "status_manager_dir", "intial_statusmanager.csv"
        )
        if os.path.exists(check_path):
            self.data_manager.status_manager = pd.read_csv(check_path, index_col=0)
            self.data_manager.reset_pool()
            print("loaded statusmanager from file")
        else:
            # self.data_manager.reset_pool()
            save_path = os.path.join(self.log_path, "status_manager_dir")
            self.data_manager.create_merged_data(path=save_path)

            print("created new statusmanager")
        self.current_oracle_step = 0

        for oracle_s in range(self.oracle_steps):

            self.set_model(
                self.current_experiment.get("model", "base"),
            )

            self.create_dataloader()
            self.create_optimizer()

            # , train_loader, val_loader, optimizer, criterion, device
            self.train(
                self.train_loader,
                self.val_loader,
                self.optimizer,
                self.criterion,
                self.device,
            )
            self.test()
            if self.perform_finetune:
                self.finetune(self.train_loader, self.pool_loader, num_epochs=10)


            self.current_oracle_step += 1
            if len(self.pool_loader) > 0:
                (
                    pool_predictions1,
                    pool_predictions2,
                    pool_labels_list,
                ) = self.pool_predictions(self.pool_loader)

                self.sampler(
                    self.data_manager,
                    number_samples=self.oracle_stepsize,
                    net=self.model,
                    predictions1=pool_predictions1,
                    predictions2=pool_predictions2,
                    thresholding=self.thresholding,
                )

                (
                    test_predictions1,
                    test_predictions2,
                    test_labels,
                ) = self.pool_predictions(self.test_loader)
                test_predictions = (test_predictions1 + test_predictions2) / 2
                test_accuracy = accuracy(test_labels, test_predictions)
                f1_score = f1(test_labels, test_predictions)

                dict_to_add = {
                    "test_loss": self.avg_test_loss,
                    "train_loss": self.avg_train_loss_hist,
                    "test_accuracy": test_accuracy,
                    "train_accuracy": self.avg_train_acc_hist,
                    "f1": f1_score,
                }

                print(dict_to_add)
                # if self.metric.lower() == "auroc":
                #     auroc_score = auroc(self.data_manager, oracle_s)

                #     dict_to_add = {"auroc": auroc_score}

                self.data_manager.add_log(
                    writer=self.writer,
                    oracle=self.oracle,
                    dataset=self.iD,
                    metric=self.metric,
                    log_dict=dict_to_add,
                    ood_ratio=self.OOD_ratio,
                    exp_name=self.exp_name,
                )
                self.save_al_logs()
        self.data_manager.status_manager.to_csv(
            os.path.join(
                self.log_path,
                "status_manager_dir",
                f"{self.exp_name}-result-statusmanager.csv",
            )
        )
