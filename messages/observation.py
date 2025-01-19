class Observation:
    def __init__(self, raw_output: str) -> None:
        """
        Initializes the observation with the raw output string.
        """
        self._raw_output = raw_output

    @property
    def raw_output(self) -> str:
        """
        Return the raw output of the observation.
        """
        return self._raw_output
    

    # In the future, we can extend this class to include methods that handle:
    # - Filtering large outputs (e.g., limiting the amount of data passed back).
    # - Ignoring or removing specific directories/files from the output (e.g., filtering out 'img/' or system files...unnecessary files for the LM to understand).
    # - Sanitizing or transforming the raw output before returning it to the LM.