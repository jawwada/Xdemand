from typing import Any

import pandas as pd
from sklearn.preprocessing import OneHotEncoder

from ctr_predictor.api_utils.schemas import VariableTypes, PytorchMLPVariableKeyValueEncoding, PytorchOneHotEncoding, \
    RegisterNewEncodingPytorchRequest, AverageCTRVariableEncoding, GetPytorchMLPEncodingsResponse
from ctr_predictor.data_operator.ctr_data import CTRData
from ctr_predictor.logging.logger import LoggerHandler
from ctr_predictor.utils.learning_tag_utils import strip_prefix

logger = LoggerHandler()  # Get the logger from the LoggerHandler instance


class Encoder:
    """
    Class to encode categorical columns in a DataFrame using different encoding methods.
    """
    ctr_data: CTRData

    def __init__(self, ctr_data: CTRData):
        """
        Constructor for the Encoder class.

        Args:
            _ctr_data: The ctr data including the sorted data frame and the lt columns.
        """
        self.ctr_data = ctr_data

    def fit_transform(self) -> (pd.DataFrame, Any, OneHotEncoder):
        """
        Fit and transform the DataFrame using the specified encoding methods.
        This method also orders the values of the data frame by date, campaign id and content unit
        It also orders the learning tag columns alphabetically, such that we recreate identical encodings for each run.

        Returns:
            The transformed DataFrame and the encodings as a sparse Matrix as well as the used encoder.
        """

        categorical_columns = set(self.ctr_data.category_columns)
        columns_to_reorder_sorted = sorted(categorical_columns)

        # order the dataframe by values and columns in order to reproduce identical encodings each day
        df = self.ctr_data.data.sort_values(by=["date", "campaign", "content_unit"]).reset_index(drop=True)
        reordered_columns = [col for col in df.columns if col not in categorical_columns] + columns_to_reorder_sorted
        # fill na with missing
        df = df[reordered_columns]
        reordered_categorical_cols = sorted(categorical_columns)
        df[reordered_categorical_cols] = df[reordered_categorical_cols].fillna('nan')
        learning_tags_df = df[self.ctr_data.encoder_columns]
        encoder_ = OneHotEncoder()
        # TODO: maybe we could make it faster here by getting destinct content units and getting the encodings for this and then merging it back somehow (how it was done before was not working due to nan values)
        encodings = encoder_.fit_transform(learning_tags_df[reordered_categorical_cols])
        df = pd.concat([df.drop(columns=reordered_categorical_cols),
                        pd.DataFrame(encodings.toarray(),
                                     columns=encoder_.get_feature_names_out(reordered_categorical_cols))], axis=1)
        return df, encodings, encoder_

    @staticmethod
    def extract_encoding_information(encoder: OneHotEncoder) -> RegisterNewEncodingPytorchRequest:
        """
        This method transforms the fitted encoder to a RegisterNewEncodingPytorchRequest object.
        The object contains for each encoding the key, value, index and its type.
        This object can be easily transformed in a json object that can be used to post to the API.
        Args:
            encoder: The fitted OneHotEncoder.

        Returns: RegisterNewEncodingPytorchRequest object
        """
        keys = encoder.feature_names_in_
        values = encoder.categories_

        index_counter = 0
        encoding_output = list()

        for key, value_list in zip(keys, values):
            for value in value_list:
                if key.startswith('external_lt'):
                    variable_type = VariableTypes.external_learning_tag
                elif key.startswith('internal_lt'):
                    variable_type = VariableTypes.internal_learning_tag
                else:
                    raise ValueError("learning tag must be external or internal")
                encoding_output.append(PytorchMLPVariableKeyValueEncoding(
                    value=value,
                    key_name=strip_prefix(key),
                    variable_type=variable_type,
                    index=index_counter))
                index_counter += 1
        campaign_previous_rate_index = AverageCTRVariableEncoding(index=index_counter)

        encodings = PytorchOneHotEncoding(key_value_variable_encodings=encoding_output,
                                          average_campaign_ctr_encoding=campaign_previous_rate_index)
        return RegisterNewEncodingPytorchRequest(encoding=encodings)

    def encode_save_data(self, encoder_path: str) -> pd.DataFrame:
        """
        Encode categorical columns based on the encoding rules.
        Returns:
            The encoded DataFrame.
        """
        df = self.ctr_data.data
        # extract learning tags for the data, and get unique rows
        learning_tags_df = df[self.ctr_data.encoder_columns]
        # drop duplicates if any and do not keep the index
        learning_tags_df = learning_tags_df.drop_duplicates().reset_index(drop=True)
        encodings = self.fit_transform()
        encodings.to_csv(encoder_path, index=False)
        logger.info(f"Encodings Saved: {encoder_path}")
        return encodings

    @staticmethod
    def decode(df: pd.DataFrame, encoder_path: str) -> pd.DataFrame:
        encodings = pd.read_csv(encoder_path)
        # Merge the encoded data with the df
        encodings['contentunit_id'] = encodings['contentunit_id'].astype(str)
        df = pd.merge(df, encodings, on=['contentunit_id'], how='left')
        logger.info(f"Decoded columns {len(encodings.columns)} with encoding rules: {encoder_path}")
        # fill the na columns for encodings to zero
        for col in encodings.columns:
            if col in df.columns:
                df[col].fillna(0, inplace=True)

        return df

    @staticmethod
    def compare_encodings(new_encoding: RegisterNewEncodingPytorchRequest,
                          encoding_to_compare: GetPytorchMLPEncodingsResponse) -> bool:
        new_encoding = new_encoding.encoding
        encoding_to_compare = encoding_to_compare.encoding

        return encoding_to_compare == new_encoding
