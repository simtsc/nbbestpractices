import re
import functools
import statistics
import numpy as np
import pandas as pd
import ipywidgets as widgets
import bqplot as bqp
import bqplot.interacts as bqpi


class TSExplorer(widgets.Box):
    """Timeseries Explorer class.
    A widget that displays tools to work with timeseries data.

    Properties
    ----------
    selected_feature: str
        Column name of data to select.
    selected_dates: list
        List with two elements: start and end date.
    selected_data: pandas.DataFrame or pandas.Series
        A pandas Dataframe or Series with the selected data.
    """

    def _gen_dataframe_tab(self):
        """Creates widgets for showing dataframe.
          - SelectMultiple to select highlight functions.
          - HTML widget to render dataframe.
    
        Returns
        -------
        widget : tab content widget
        """
        def highlight(s, func, color):
            """
            Highlight values with color if value equals return value of func.
            """
            is_true = s == func(s)
            return [f'background-color: {color}' if v else '' for v in is_true]

        hfuncs= {
            'min': functools.partial(highlight, func=min, color='red'),
            'max': functools.partial(highlight, func=max, color='lime'),
            'median': functools.partial(highlight, func=statistics.median_low, color='yellow')
        }

        def render_highlight(change):
            """Callback to highlight values in dataframe
    
            Parameters
            ----------
            change : dict
                Widget and changed values.
            """
            dfstyle = self._data.style
            for fname in change.new:
                if fname in hfuncs:
                    dfstyle = dfstyle.apply(hfuncs[fname])
            dfhtml.value = dfstyle.render()

        hlselfuncs = widgets.SelectMultiple(options=hfuncs.keys(), rows=len(hfuncs), description='Highlight:')
        # register callback for value changes in selection box
        hlselfuncs.observe(render_highlight, ['value'])
        dfhtml = widgets.HTML(value=self._data.style.render())
        return widgets.HBox(children=[hlselfuncs, dfhtml])

    def _gen_series_tab(self):
        """Creates widgets for selecting timeseries data.
          - Dropdown to select column from dataframe.
          - Interactive bqplot with BrushIntervalSelector.
    
        Returns
        -------
        widget : tab content widget
        """
        scales = {
            'x': bqp.DateScale(), 
            'y': bqp.LinearScale(), 
            'color': bqp.ColorScale(scheme='oranges')
        }

        axes = [
            bqp.Axis(scale=scales['x'], label='Date', num_ticks=int(len(self._data.index) / 2)),
            bqp.Axis(scale=scales['y'], label='Value', orientation='vertical')
        ]

        mark = bqp.Lines(scales=scales)

        feature_selector = widgets.Dropdown(options=self._data.columns,
                                            description='Feature:')

        def feature_selection_callback(change):
            """Callback to update graph when new data has been selected
    
            Parameters
            ----------
            change : dict
                Widget and changed values.
            """
            self._selected_feature = change.new
            fig.title = f'Feature: {change.new}'
            series = self._data[change.new]
            mark.x = series.index
            mark.y = series.values
        
        # register callback for dropdown value-change events
        feature_selector.observe(feature_selection_callback, ['value'])

        def brush_sel_dt_callback(change):
            """Callback to update graph when new data has been selected
    
            Parameters
            ----------
            change : dict
                Widget and changed values.
            """
            tstamps = selector.selected
            if isinstance(tstamps, np.ndarray):
                tstamps = tstamps.tolist()
            if not selector.brushing and tstamps:
                # extract year and month from timestamp string: e.g. 2000-03-11T06:51:50.089000 -> 2000-03
                dates = [pd.to_datetime(re.split(r'-\d\dT', str(ts))[0]) for ts in tstamps]
                self._selected_dates = dates

        selector = bqpi.BrushIntervalSelector(scale=scales['x'], color='blue')
        # register callback for BrushIntervalSelector brushing events
        selector.observe(brush_sel_dt_callback, ['brushing'])

        fig = bqp.Figure(marks=[mark], 
                         axes=axes, 
                         interaction=selector, 
                         layout=widgets.Layout(width='880px', height='380px'),
                         animation_duration=1000)
        
        def reset_btn_click(b):
            """Reset selector and update instance properties accordingly.
    
            Parameters
            ----------
            b : Button
                Button instance.
            """
            selector.reset()
            self.reset()
        
        reset_btn = widgets.Button(description='reset')
        reset_btn.on_click(reset_btn_click)

        return widgets.VBox(children=[widgets.HBox(children=[feature_selector, reset_btn]), fig])

    def __init__(self, tsdf, **kwargs):
        """Constructor.
    
        Parameters
        ----------
        tsdf : pandas.Dataframe
            Dataframe containing data for exploration.
        """
        super().__init__(**kwargs)
        self._data = tsdf
        self._selected_feature = None
        self._selected_dates = None

        tab_data = self._gen_dataframe_tab()
        tab_series = self._gen_series_tab()

        tabs = widgets.Tab(children=[tab_data, tab_series], layout=self.layout)
        tabs.set_title(0, 'Dataframe')
        tabs.set_title(1, 'Feature Selector')
        self.children = [tabs]
    
    def reset(self, selected_feature=True, selected_dates=True):
        """Reset the selected filters.

        Parameters
        ----------
        selected_feature : bool
            Reset selected feature. Use all dataframe columns again.
        selected_dates : bool
            Reset selected dates. Use all rows.
        """
        if selected_feature:
            self._selected_feature = None
        if selected_dates:
            self._selected_dates = None
    
    @property
    def selected_feature(self):
        """Getter for selected feature.
    
        Returns
        -------
        str : name of selected column
        """
        return self._selected_feature

    @property
    def selected_dates(self):
        """
        Getter for selected dates.

        Returns
        -------
        list : start and end dates
        """
        return self._selected_dates

    @property
    def selected_data(self):
        """
        Getter for selected data.
        Applies selected feature and selected dates to dataframe.

        Returns
        -------
        pandas.Dataframe or pandas.Series : selected data
        """
        d = self._data
        if self._selected_dates:
            d = self._data.loc[self._selected_dates[0]: 
                               self._selected_dates[1]]
        if self._selected_feature:
            d = d[self._selected_feature]
        return d
