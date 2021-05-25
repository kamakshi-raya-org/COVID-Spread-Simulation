import random
import fastrand
import pandas as pd
import networkx as nx
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import threading
import time
import plotly.express as px
from networkx.generators.degree_seq import expected_degree_graph
pio.renderers.default = 'browser'
a=1
time_=[]
people=[]
threads=[]
while(a!=2):
    symptomatic=[]
    nonsymptomatic=[]
    notsick=[]
    days=[]
    n_iters =int(input("Enter the number of days: (25) "))
    prob =float(input('Enter the probability of getting infected: (0.9) '))
    #It is used in the function _create_new_sick_nodes.Consider the range of fractions from 0 to 1. There is a greater length from 0 to 0.9(numbers less than 0.9) than from 0.9 to 1.The function used to generate the random values is fastrand.pcg32bounded(1000)/1000. Thus if a random number is chosen which is less than 0.9, the node gets infected. However if it is greater than 0.9, the node does not get infected. Thus it is very likely to be infected. All possible random values must be less than 1. Thus if prob is set to 1, all the nodes will get infected.
    n_nodes =int(input('Enter the number of people in the network: (200) '))
    mean_inters =int(input('Enter the average number of nodes connected to each node: (8) '))
    #The network is stored as a graph, and some nodes will have more or less than the entered number of neighbours. But the average number of neighbours is about mean_inters.
    std_dev =int(input('Enter the standard deviation for number of neighbours: (4) '))
    n_sick =int(input('Enter the initial number of infected people: (15) '))
    #The sick people will be randomly chosen in the function generate_network.
    interval =int(input('Enter the number of days after which the simulation is to be created: (5) '))
    #On the 5th, 10th, 15th, 20th etc days, new stages of the network will be appended to the networks list for visualizing the network on that day
    #k=0.1
    prop_social_distancing =float(input('Enter the fraction of people who practice social distancing: (0.25) '))
    effectiveness_social_distancing =float(input("How much less prone are the people who have practiced social distancing: (0.25) "))
     #The new probability of those who social-distance being infected is this value * the initial prob, ie 0.25 * 0.9 = 0.225. In the function generate_network, the number of connections for those who social-distance is reduced to their original values * this value. This signifies a reduced contact with people
    prop_self_isolating =float(input("Enter the portion of people who isolate themselves: (0.05) "))
    #the number of connections for these people is set to 0
    num_threads=int(input("Enter the number of threads: "))
    threads.append(num_threads)
    def generate_network(n_nodes, mean_inters, std_dev, n_sick):
        # Create a graph with entered attributes
        n_ties = pd.Series(map(int, np.round(np.random.normal(mean_inters, std_dev, n_nodes))))
        #This simply creates a pandas series of random integers with the given mean and standard deviation. The integers stand for the number of neighbours/connections each person has.
        distancers = random.sample(list(n_ties.index), round(prop_social_distancing * n_nodes))
        n_ties[distancers] = n_ties[distancers] * effectiveness_social_distancing
        #Make the social distancers a little safer
        isolaters = random.sample(list(n_ties.index), round(prop_self_isolating * n_nodes))
        n_ties[isolaters] = 0
        #People under isolation dont get sick and dont get others sick
        G = expected_degree_graph(n_ties, selfloops=False)
        # The graph object is created
        nx.set_node_attributes(G, 0, 'COVID-19')
        nx.set_node_attributes(G, 0, 'Time Sick')
        nx.set_node_attributes(G, 0, 'Symptomatic')
        nx.set_node_attributes(G, 0, 'Time Showing')
        #Each node/person in the graph will have the above attributes.The attributes will later be set to 1 showing that they are present, or increase with time.
        sick_nodes = random.sample(list(G.nodes), n_sick)
        for node in sick_nodes:
            G.nodes[node]['COVID-19'] = 1
        #Some nodes are randomly chosen and made sick, and their COVID-19 attribute is set to 1.
        return(G, sick_nodes)
    def _create_new_sick_nodes(G, sick_nodes, showing, prob):
        for node in sick_nodes:
            #Iterate through each contact with the sick person
            for edge in G[node]:
                if edge not in sick_nodes and edge not in showing:
                    if fastrand.pcg32bounded(1000)/1000 < prob:
                        G[node][edge]['COVID-19'] = 1
                        sick_nodes.append(edge)
                #The function used to generate the random values is fastrand.pcg32bounded(1000)/1000. It will generate a random number from 0 to 999 inclusive. This value will then be divided by 1000, so the line will return a random float between 0 and 1. The function uses pcg(Preconditioned congugate gradient) algorithm, which apparently makes it faster than the inbuilt random methods.Initially, some nodes are infected with COVID-19 and later, these nodes spread it with the probability entered (0.9). After the initial state, every new infection comes from a previous infection. So if a random number is chosen which is less than 0.9, the node gets infected. However if it is greater than 0.9, the node does not get infected. Thus it is very likely to be infected.
        return(G, sick_nodes)
    def _update_sick_nodes_threads(thread_id, G, sick_nodes, size):
        for i in range(thread_id, size, num_threads):
            G.nodes[sick_nodes[i]]['Time Sick'] += 1
            #Counting the amount of time a node has been sick
    def _update_sick_nodes(G, sick_nodes):
        threads_list=[]
        try:
            for t in range(num_threads):
                thread_curr = threading.Thread(target=_update_sick_nodes_threads, args = (t, G, sick_nodes, len(sick_nodes)))
                threads_list.append(thread_curr)
                thread_curr.start()
            for thread_curr in threads_list:
                thread_curr.join()
        except:
           print ("Error: unable to start thread")
        return(G, sick_nodes)
    #Implementing the _update_sick_nodes function in multiple threads

    def _show_symptoms_threads(thread_id, G, sick_nodes, size, showing, lock_sick, lock_showing, to_be_removed):
        #Decide who should go from carrying to showing symptoms
        for i in range(thread_id, size, num_threads):
            if random.normalvariate(8, 2) < G.nodes[sick_nodes[i]]['Time Sick']:
                G.nodes[sick_nodes[i]]['Symptomatic'] = 1
                G.nodes[sick_nodes[i]]['Time Showing'] = 1
                with lock_sick:
                    to_be_removed.append(i)
                with lock_showing:
                    showing.append(sick_nodes[i])
        #This randomly makes nodes(people) show symptoms when the time they've been sick is close to 8. And if one is showing symptoms, it is removed from the sick nodes
    def _show_symptoms(G, sick_nodes, showing):
        #Decide who should go from carrying to showing symptoms
        threads_list = []
        to_be_removed = []
        lock_showing = threading.Lock()
        lock_sick = threading.Lock()
        try:
            for t in range(num_threads):
                thread_curr = threading.Thread(target=_show_symptoms_threads, args = (t, G, sick_nodes, len(sick_nodes), showing, lock_sick, lock_showing, to_be_removed))
                threads_list.append(thread_curr)
                thread_curr.start()
            for thread_curr in threads_list:
                thread_curr.join()
        except:
           print ("Error: unable to start thread")

        for index in sorted(to_be_removed, reverse=True):
            del sick_nodes[index]
        return(G, sick_nodes, showing)
        

    def run_iteration(G, sick_nodes, showing, prob):
        G, sick_nodes = _create_new_sick_nodes(G, sick_nodes, showing, prob)
        G, sick_nodes = _update_sick_nodes(G, sick_nodes)
        G, sick_nodes, showing = _show_symptoms(G, sick_nodes, showing)
        #This is a single function to call all the previous ones in one go
        return(G, sick_nodes, showing)
    def visualize_network(G, day):
       #reference from https://plot.ly/python/network-graphs/
        nx.set_node_attributes(G, nx.drawing.spring_layout(G,k=1), 'pos')
        #c=200, k=1; c=2000, k=0.5
        node_color = []
        node_text = []
        sym=0
        nsym=0
        nsick=0
        for node, adjacencies in enumerate(G.adjacency()):
            if G.nodes[node]['Symptomatic'] != 0:
                node_text.append('Symptomatic, Sick')
                node_color.append('red')
                sym+=1
            elif G.nodes[node]['COVID-19'] != 0:
                node_text.append('Sick, Non-Symptomatic')
                node_color.append('lightyellow')
                nsym+=1
            else:
                node_text.append('Not Sick')
                node_color.append('lightgreen')
                nsick+=1
        symptomatic.append(sym)
        nonsymptomatic.append(nsym)
        notsick.append(nsick)
        days.append(day)
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = G.nodes[edge[0]]['pos']
            x1, y1 = G.nodes[edge[1]]['pos']
            edge_x.append(x0)
            edge_x.append(x1)
            edge_x.append(None)
            edge_y.append(y0)
            edge_y.append(y1)
            edge_y.append(None)
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')
        node_x = []
        node_y = []
        for node in G.nodes():
            x, y = G.nodes[node]['pos']
            node_x.append(x)
            node_y.append(y)
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            marker=dict(
                showscale=True,
                color=[],
                size=10,
                colorbar=dict(
                    thickness=15,
                    title='',
                    xanchor='left',
                    titleside='right'
                ),
                line_width=2))
        node_trace.marker.color = node_color
        node_trace.text = node_text
        fig = go.Figure(data=[edge_trace, node_trace],
                     layout=go.Layout(
                        title='DAY  {}'.format(day),
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        annotations=[ dict(
                            text='Day {}'.format(day),
                            showarrow=False,
                            xref="paper", yref="paper",
                            x=0.005, y=-0.002 ) ],
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))
        pio.show(fig)
        #This uses networkx and plotly to visualize the network.
        return(True)

    if __name__ == '__main__':
        start = time.time()
        G, sick_nodes = generate_network(n_nodes, mean_inters, std_dev, n_sick)
        #This function is called to initialise the network
        showing = []
        networks = []
        #The simulation will run showing the number of days specified
        for iters in range(n_iters):
            if iters % interval == 0:
                networks.append(G.copy())
            G, sick_nodes, showing = run_iteration(G, sick_nodes, showing, prob)
            #The function is called to update the state of the network.
        for n, G in enumerate(networks):
            day = n* interval
            visualize_network(G, day)
            #The network is visualized for each day it was saved.
        end = time.time()
        list_of_tuples = list(zip(notsick,nonsymptomatic,symptomatic))
        list_of_tuples
        df = pd.DataFrame(list_of_tuples,columns = ['Not-Sick', 'Non-Symptomatic','Symptomatic'],index=days)
        fig = px.bar(df)
        fig.show()
        print(f"Runtime of the program is {end - start} seconds")
        time_.append(end-start)
        a=int(input('[1]Run the Simulation\n[2]Exit'))
print("Simulation Terminated!")
