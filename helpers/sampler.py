import numpy as np


def random_sample(dataset_manager, number_samples, net, predictions=None, weights = None):
    """random_sample [Randomly adds images from the unlabelled pool to the training set]
    Args:
        dataset_manager ([object]): [description]
        number_samples ([int]): [oracle stepsize]
        net ([nn.Module]): [description]
        predictions ([type], optional): [description]. Defaults to None.
    """

    status_manager = dataset_manager.status_manager
    pool_samples_count = len(status_manager[status_manager["status"] == 0])

    assert pool_samples_count > 0, "No sample left in pool to label"
    assert (
        pool_samples_count > number_samples
    ), f"Number of samples to be labelled is less than the number of samples left in pool : {pool_samples_count} < {number_samples}"

    inds = np.random.choice(
        status_manager[status_manager["status"] == 0].index.tolist(),
        replace=False,
        size=number_samples,
    )
    iteration = 1 + status_manager["status"].max()
    status_manager.iloc[inds, -1] = iteration * status_manager.iloc[inds, -2]

    return None


def uncertainity_sampling_least_confident(
    dataset_manager, number_samples, net, predictions=None, weights = None
):
    """uncertainity_sampling_least_confident [Uses least confidence to sample training data from the unlabelled poo]

        [This function selects num_samples from the pool of  all the unlabelled data at random and add them to labelled training data assumes prediction is in shape (number_of_samples,num_classes)
    ]

        Args:
            dataset_manager ([object]): [description]
            number_samples ([int]): [oracle stepsize]
            net ([nn.Module]): [description]
            predictions ([type], optional): [description]. Defaults to None.
    """

    status_manager = dataset_manager.status_manager
    pool_samples_count = len(status_manager[status_manager["status"] == 0])

    assert pool_samples_count > 0, "No sample left in pool to label"
    assert (
        pool_samples_count > number_samples
    ), f"Number of samples to be labelled is less than the number of samples left in pool : {pool_samples_count} < {number_samples}"

    if weights is not None:
        predictions = weights*predictions
    inds = np.argsort(np.max(predictions, axis=1))[:number_samples]
    inds = status_manager[status_manager["status"] == 0].index[inds]
    iteration = 1 + status_manager["status"].max()
    status_manager.iloc[inds, -1] = iteration * status_manager.iloc[inds, -2]

    return None


def uncertainity_sampling_highest_entropy(
    dataset_manager, number_samples, net, predictions=None, weights = None
):
    """uncertainity_sampling_highest_entropy [Uses highest entropy to sample training data from the unlabelled pool]

    [This function selects num_samples from the pool of  all the unlabelled data at random and add them to labelled training data assumes prediction is in shape (number_of_samples,num_classes)]

    Args:
        dataset_manager ([type]): [description]
        number_samples ([type]): [description]
        net ([type]): [description]
        predictions ([type], optional): [description]. Defaults to None.
    """

    status_manager = dataset_manager.status_manager
    pool_samples_count = len(status_manager[status_manager["status"] == 0])

    assert pool_samples_count > 0, "No sample left in pool to label"
    assert (
        pool_samples_count > number_samples
    ), f"Number of samples to be labelled is less than the number of samples left in pool : {pool_samples_count} < {number_samples}"

    entropy = np.sum(predictions * np.log(predictions + 1e-9), axis=1)
    if weights is not None:
        entropy = np.squeeze(weights)*entropy
    inds = np.argsort(entropy)[:number_samples]
    inds = status_manager[status_manager["status"] == 0].index[inds]
    iteration = 1 + status_manager["status"].max()
    status_manager.iloc[inds, -1] = iteration * status_manager.iloc[inds, -2]

    return None


def extra_class_sampler(extra_class_thresholding):
    def extra_class_sampler(dataset_manager, number_samples, net, predictions=None, weights = None): 
        """uncertainity_sampling_highest_entropy [Uses highest entropy to sample training data from the unlabelled 
        pool with OoD samples as an extra class. The OoD class is separated from the rest and remaining class probablities
        are re-noramlized to sum to 1. The entropy value of these re-normalized probablities is used for distinguishing
        sampling. Two methods are implementated to distinguish between OoD and In-dist before sampling:

            1) Hard thresholding:  All images with OoD Class as highest probablilty are not considered when sampling]
            2) Soft thresholding: The entropy values for weighted with (1-OoD_Class_Probablity) and the highest value
                                    among them are selected for sampling. 

        [This function selects num_samples from the pool of  all the unlabelled data at random and add them to labelled
         training data assumes prediction is in shape (number_of_samples,num_classes)]

        Args:
            dataset_manager ([type]): [description]
            number_samples ([type]): [description]
            net ([type]): [description]
            predictions ([type], optional): [description]. Defaults to None.
        """

        status_manager = dataset_manager.status_manager
        pool_samples_count = len(status_manager[status_manager["status"] == 0])
        
        assert pool_samples_count > 0, "No sample left in pool to label"
        assert (
            pool_samples_count > number_samples
        ), f"Number of samples to be labelled is less than the number of samples left in pool : {pool_samples_count} < {number_samples}"

        if extra_class_thresholding=='soft':
            OoD_class_probablities = 1-predictions[:,-1]
        elif extra_class_thresholding=='hard':
            inds_OoD = ~(predictions.argmax(axis=1)==predictions.shape[1])
        

        predictions = predictions[:,:-1]
        predictions = predictions/np.sum(predictions, axis=1, keepdims=True)

        entropy = np.sum(predictions * np.log(predictions + 1e-9), axis=1)
        
        if extra_class_thresholding=='soft':
            entropy = np.squeeze(OoD_class_probablities)*entropy
            inds = np.argsort(entropy)[:number_samples]
            inds = status_manager[status_manager["status"] == 0].index[inds]
        elif extra_class_thresholding=='hard':
            temp_status_manager = status_manager[status_manager["status"] == 0].copy()
            temp_status_manager['OoD'] =  inds_OoD
            temp_status_manager['entropy'] = entropy
            temp_status_manager = temp_status_manager[temp_status_manager['OoD']]
            temp_status_manager.sort_values('entropy', inplace=True)
            inds = temp_status_manager.index[:number_samples]

        iteration = 1 + status_manager["status"].max()
        status_manager['status'].iloc[inds] = iteration * status_manager['source'].iloc[inds]

        return None
    return extra_class_sampler


def gen0din_sampler(dataset_manager, number_samples, net, predictions=None):

    return None


def DDU_sampler(dataset_manager, number_samples, net, predictions=None):

    return None